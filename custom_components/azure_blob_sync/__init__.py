import logging
from typing import Optional
from datetime import timedelta
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from .const import (
    DOMAIN,
    CONF_CONNECTION_STRING,
    CONF_CONTAINER_NAME,
    CONF_FOLDERS,
    CONF_LOCAL_FOLDER,
    CONF_BLOB_FOLDER,
    CONF_SYNC_MODES,
    SYNC_MODE_MANUAL,
    SYNC_MODE_SCHEDULE,
    SYNC_MODE_EVENT,
    CONF_SYNC_INTERVAL,
    CONF_TRIGGER_ENTITY,
    CONF_TRIGGER_STATE,
)
from .azure_blob_sync import AzureBlobSync

TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SYNC_INTERVAL): cv.positive_int,
        vol.Optional(CONF_TRIGGER_ENTITY): cv.entity_id,
        vol.Optional(CONF_TRIGGER_STATE): cv.string,
    }
)

FOLDER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LOCAL_FOLDER): cv.string,
        vol.Required(CONF_BLOB_FOLDER): cv.string,
        vol.Required(CONF_SYNC_MODES): vol.All(
            cv.ensure_list,
            [vol.In([SYNC_MODE_MANUAL, SYNC_MODE_SCHEDULE, SYNC_MODE_EVENT])],
        ),
        vol.Optional(CONF_TRIGGER_ENTITY): cv.entity_id,
        vol.Optional(CONF_TRIGGER_STATE): cv.string,
        vol.Optional(CONF_SYNC_INTERVAL): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CONNECTION_STRING): cv.string,
                vol.Required(CONF_CONTAINER_NAME): cv.string,
                vol.Required(CONF_FOLDERS): vol.All(cv.ensure_list, [FOLDER_SCHEMA]),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Azure Blob Sync from YAML configuration."""
    _LOGGER.debug("Starting async_setup for azure_blob_sync")
    
    try:
        conf = config.get(DOMAIN)
        if conf is None:
            _LOGGER.error("No configuration found for azure_blob_sync")
            return False

        _LOGGER.debug("Configuration found: %s", conf)

        try:
            azure_blob_sync = AzureBlobSync(conf[CONF_CONNECTION_STRING])
            _LOGGER.debug("AzureBlobSync instance created successfully")
        except Exception as e:
            _LOGGER.error("Failed to create AzureBlobSync instance: %s", str(e))
            return False

        async def sync_folder(local_folder, blob_folder):
            """Sync a single folder pair."""
            _LOGGER.info(f"Starting sync for {local_folder} to {blob_folder}")
            try:
                await azure_blob_sync.create_container(conf[CONF_CONTAINER_NAME])
                await azure_blob_sync.sync_folder_to_blob(
                    conf[CONF_CONTAINER_NAME], local_folder, blob_folder
                )
                _LOGGER.info(f"Sync completed for {local_folder} to {blob_folder}")
            except Exception as e:
                _LOGGER.error(f"Error during sync of {local_folder} to {blob_folder}: {str(e)}")

        async def sync_all_folders(_: Optional[ServiceCall] = None):
            """Sync all configured folder pairs."""
            _LOGGER.info("Starting folder sync for all configured folders")
            for folder_config in conf[CONF_FOLDERS]:
                await sync_folder(folder_config[CONF_LOCAL_FOLDER], folder_config[CONF_BLOB_FOLDER])
            _LOGGER.info("Folder sync completed successfully for all folders")

        # Register global sync service
        hass.services.async_register(DOMAIN, "sync_all", sync_all_folders)
        _LOGGER.info("Registered 'sync_all' service")

        # Set up individual folder syncs and triggers
        for index, folder_config in enumerate(conf[CONF_FOLDERS]):
            local_folder = folder_config[CONF_LOCAL_FOLDER]
            blob_folder = folder_config[CONF_BLOB_FOLDER]
            sync_modes = folder_config[CONF_SYNC_MODES]

            # Register individual sync service
            async def sync_single_folder(_: Optional[ServiceCall], l_folder=local_folder, b_folder=blob_folder):
                await sync_folder(l_folder, b_folder)

            hass.services.async_register(DOMAIN, f"sync_folder_{index}", sync_single_folder)
            _LOGGER.info(f"Registered 'sync_folder_{index}' service for {local_folder} to {blob_folder}")

            # Set up scheduled sync if configured
            if SYNC_MODE_SCHEDULE in sync_modes and CONF_SYNC_INTERVAL in folder_config:
                interval = timedelta(minutes=folder_config[CONF_SYNC_INTERVAL])
                async_track_time_interval(hass, lambda _: sync_single_folder(None), interval)
                _LOGGER.info(f"Scheduled sync set up for folder {index} with interval: {folder_config[CONF_SYNC_INTERVAL]} minutes")

            # Set up event-based sync if configured
            if (
                SYNC_MODE_EVENT in sync_modes
                and CONF_TRIGGER_ENTITY in folder_config
                and CONF_TRIGGER_STATE in folder_config
            ):
                entity_id = folder_config[CONF_TRIGGER_ENTITY]
                trigger_state = folder_config[CONF_TRIGGER_STATE]

                def create_state_change_listener(local_f, blob_f):
                    async def state_change_listener(entity_id, old_state, new_state):
                        if new_state and new_state.state == trigger_state:
                            await sync_folder(local_f, blob_f)
                    return state_change_listener

                listener = create_state_change_listener(local_folder, blob_folder)
                async_track_state_change(hass, entity_id, listener)
                _LOGGER.info(f"Event-based sync set up for folder {index}, entity: {entity_id}, trigger state: {trigger_state}")

        _LOGGER.info("Azure Blob Sync setup completed successfully")
        return True

    except Exception as e:
        _LOGGER.error("Unexpected error during Azure Blob Sync setup: %s", str(e))
        return False
