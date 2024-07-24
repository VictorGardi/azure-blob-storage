import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
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

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CONNECTION_STRING): cv.string,
                vol.Required(CONF_CONTAINER_NAME): cv.string,
                vol.Required(CONF_LOCAL_FOLDER): cv.string,
                vol.Required(CONF_BLOB_FOLDER): cv.string,
                vol.Required(CONF_SYNC_MODES): vol.All(
                    cv.ensure_list,
                    [vol.In([SYNC_MODE_MANUAL, SYNC_MODE_SCHEDULE, SYNC_MODE_EVENT])],
                ),
                vol.Optional(CONF_SYNC_INTERVAL): cv.positive_int,
                vol.Optional(CONF_TRIGGER_ENTITY): cv.entity_id,
                vol.Optional(CONF_TRIGGER_STATE): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Azure Blob Sync from YAML configuration."""
    _LOGGER.debug("Starting async_setup for azure_blob_sync")
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
    async def sync_folders():
        """Sync folders."""
        await azure_blob_sync.create_container(conf[CONF_CONTAINER_NAME])
        await azure_blob_sync.sync_folder_to_blob(
            conf[CONF_CONTAINER_NAME], conf[CONF_LOCAL_FOLDER], conf[CONF_BLOB_FOLDER]
        )

    hass.services.async_register(DOMAIN, "sync", sync_folders)
    _LOGGER.info("registered service")

    sync_modes = conf[CONF_SYNC_MODES]

    if SYNC_MODE_SCHEDULE in sync_modes and CONF_SYNC_INTERVAL in conf:
        interval = timedelta(minutes=conf[CONF_SYNC_INTERVAL])
        async_track_time_interval(hass, sync_folders, interval)

    #if (
    #    SYNC_MODE_EVENT in sync_modes
    #    and CONF_TRIGGER_ENTITY in conf
    #    and CONF_TRIGGER_STATE in conf
    #):
    #    entity_id = conf[CONF_TRIGGER_ENTITY]
    #    trigger_state = conf[CONF_TRIGGER_STATE]

    #    async def state_change_listener(new_state):
    #        if new_state.state == trigger_state:
    #            await sync_folders()

    #    async_track_state_change(hass, entity_id, state_change_listener)

    return True
