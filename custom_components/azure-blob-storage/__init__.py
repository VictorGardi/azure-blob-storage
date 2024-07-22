from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from datetime import timedelta

from .const import (
    DOMAIN,
    CONF_CONNECTION_STRING,
    CONF_CONTAINER_NAME,
    CONF_LOCAL_FOLDER,
    CONF_BLOB_FOLDER,
    CONF_SYNC_MODES,
    SYNC_MODE_SCHEDULE,
    SYNC_MODE_EVENT,
    CONF_SYNC_INTERVAL,
    CONF_TRIGGER_ENTITY,
    CONF_TRIGGER_STATE,
)
from .azure_blob_sync import AzureBlobSync


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Azure Blob Sync from a config entry."""
    azure_blob_sync = AzureBlobSync(entry.data[CONF_CONNECTION_STRING])

    async def sync_folders():
        """Sync folders."""
        await azure_blob_sync.create_container(entry.data[CONF_CONTAINER_NAME])
        await azure_blob_sync.sync_folder_to_blob(
            entry.data[CONF_CONTAINER_NAME],
            entry.data[CONF_LOCAL_FOLDER],
            entry.data[CONF_BLOB_FOLDER],
        )

    hass.services.async_register(DOMAIN, "sync", sync_folders)

    sync_modes = entry.data[CONF_SYNC_MODES]

    if SYNC_MODE_SCHEDULE in sync_modes:
        interval = timedelta(minutes=entry.data[CONF_SYNC_INTERVAL])
        async_track_time_interval(hass, sync_folders, interval)

    if SYNC_MODE_EVENT in sync_modes:
        entity_id = entry.data[CONF_TRIGGER_ENTITY]
        trigger_state = entry.data[CONF_TRIGGER_STATE]

        async def state_change_listener(entity):
            if entity.state == trigger_state:
                await sync_folders()

        async_track_state_change(hass, entity_id, state_change_listener)

    return True
