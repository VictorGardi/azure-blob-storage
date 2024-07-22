import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_CONNECTION_STRING,
    CONF_CONTAINER_NAME,
    CONF_LOCAL_FOLDER,
    CONF_BLOB_FOLDER,
    CONF_SYNC_MODES,
    CONF_SYNC_INTERVAL,
    CONF_TRIGGER_ENTITY,
    CONF_TRIGGER_STATE,
    SYNC_MODE_MANUAL,
    SYNC_MODE_SCHEDULE,
    SYNC_MODE_EVENT,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            # Validate the basic config...
            self.init_info = user_input
            return await self.async_step_sync_config()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONNECTION_STRING): str,
                    vol.Required(CONF_CONTAINER_NAME): str,
                    vol.Required(CONF_LOCAL_FOLDER): str,
                    vol.Required(CONF_BLOB_FOLDER): str,
                }
            ),
            errors=errors,
        )

    async def async_step_sync_config(self, user_input=None):
        errors = {}
        if user_input is not None:
            sync_modes = user_input[CONF_SYNC_MODES]
            next_step = None
            if SYNC_MODE_SCHEDULE in sync_modes:
                next_step = "schedule"
            elif SYNC_MODE_EVENT in sync_modes:
                next_step = "event"
            else:
                return self.async_create_entry(
                    title="Azure Blob Sync", data={**self.init_info, **user_input}
                )

            self.init_info.update(user_input)
            return await getattr(self, f"async_step_{next_step}")()

        return self.async_show_form(
            step_id="sync_config",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SYNC_MODES): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"label": "Manual", "value": SYNC_MODE_MANUAL},
                                {"label": "Scheduled", "value": SYNC_MODE_SCHEDULE},
                                {"label": "Event-triggered", "value": SYNC_MODE_EVENT},
                            ],
                            multiple=True,
                            mode=selector.SelectSelectorMode.CHECKBOX,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_schedule(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.init_info.update(user_input)
            if SYNC_MODE_EVENT in self.init_info[CONF_SYNC_MODES]:
                return await self.async_step_event()
            return self.async_create_entry(title="Azure Blob Sync", data=self.init_info)

        return self.async_show_form(
            step_id="schedule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SYNC_INTERVAL): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=1440, unit_of_measurement="minutes"
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_event(self, user_input=None):
        errors = {}
        if user_input is not None:
            self.init_info.update(user_input)
            return self.async_create_entry(title="Azure Blob Sync", data=self.init_info)

        return self.async_show_form(
            step_id="event",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TRIGGER_ENTITY): selector.EntitySelector(),
                    vol.Required(CONF_TRIGGER_STATE): str,
                }
            ),
            errors=errors,
        )
