import os
import asyncio
from typing import Optional
from pathlib import Path
from azure.storage.blob.aio import BlobServiceClient, ContainerClient
from azure.core.exceptions import ResourceExistsError


class AzureBlobSync:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    async def _get_blob_service_client(self) -> BlobServiceClient:
        return BlobServiceClient.from_connection_string(self.connection_string)

    async def upload_file(
        self,
        path_to_file: str,
        container_name: str,
        path_to_blob_file: Optional[str] = None,
    ) -> None:
        path_to_blob_file = path_to_blob_file or Path(path_to_file).name
        async with await self._get_blob_service_client() as client:
            container_client = client.get_container_client(container_name)
            await self._upload_file(container_client, path_to_file, path_to_blob_file)

    async def create_container(self, container_name: str) -> None:
        async with await self._get_blob_service_client() as client:
            try:
                await client.create_container(container_name)
                print(f"Container '{container_name}' created successfully.")
            except ResourceExistsError:
                print(f"Container '{container_name}' already exists.")

    async def sync_folder_to_blob(
        self, container_name: str, local_folder_path: str, blob_folder_path: str
    ) -> None:
        async with await self._get_blob_service_client() as client:
            container_client = client.get_container_client(container_name)
            tasks = [
                self._upload_file(
                    container_client,
                    os.path.join(root, file),
                    os.path.join(
                        blob_folder_path,
                        os.path.relpath(os.path.join(root, file), local_folder_path),
                    ).replace("\\", "/"),
                )
                for root, _, files in os.walk(local_folder_path)
                for file in files
            ]
            await asyncio.gather(*tasks)

    @staticmethod
    async def _upload_file(
        container_client: ContainerClient, local_file_path: str, blob_path: str
    ) -> None:
        try:
            with open(local_file_path, mode="rb") as data:
                await container_client.upload_blob(
                    name=blob_path, data=data, overwrite=True
                )
            print(f"Uploaded {local_file_path} to {blob_path}")
        except Exception as e:
            print(f"Failed to upload {local_file_path}: {str(e)}")


async def main():
    connection_string = os.environ["AZURE_CONN_STR"]
    container_name = "homeacontainer"
    local_folder_path = (
        "/home/victor/personal/azure-blob-storage/custom_components/azure-blob-storage"
    )
    blob_folder_path = "test"

    blob_sync = AzureBlobSync(connection_string)
    await blob_sync.create_container(container_name)
    await blob_sync.sync_folder_to_blob(
        container_name, local_folder_path, blob_folder_path
    )


if __name__ == "__main__":
    asyncio.run(main())
