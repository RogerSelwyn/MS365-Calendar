"""Configuration flow for the MS365 platform."""

from copy import deepcopy

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import (
    config_entries,  # exceptions
)
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import entity_registry
from homeassistant.helpers.selector import BooleanSelector

from ..classes.config_entry import MS365ConfigEntry
from ..const import (
    CONF_ENABLE_UPDATE,
    CONF_ENTITY_NAME,
    CONF_SHARED_MAILBOX,
)
from ..helpers.utils import add_attribute_to_item
from .const_integration import (
    CONF_BASIC_CALENDAR,
    CONF_CALENDAR_LIST,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_GROUPS,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_SENSITIVITY_EXCLUDE,
    CONF_TRACK,
    CONF_TRACK_NEW_CALENDAR,
    YAML_CALENDARS_FILENAME,
)
from .filemgmt_integration import (
    build_yaml_file_path,
    build_yaml_filename,
    read_calendar_yaml_file,
    write_calendar_yaml_file,
    write_yaml_file,
)
from .utils_integration import build_calendar_entity_id

BOOLEAN_SELECTOR = BooleanSelector()


def integration_reconfigure_schema(entry_data):
    """Extend the scheme with integration specific attributes."""
    return {
        vol.Optional(
            CONF_ENABLE_UPDATE, default=entry_data[CONF_ENABLE_UPDATE]
        ): cv.boolean,
        vol.Optional(
            CONF_BASIC_CALENDAR, default=entry_data[CONF_BASIC_CALENDAR]
        ): cv.boolean,
        vol.Optional(CONF_GROUPS, default=entry_data[CONF_GROUPS]): cv.boolean,
        vol.Optional(
            CONF_SHARED_MAILBOX,
            description={"suggested_value": entry_data.get(CONF_SHARED_MAILBOX, None)},
        ): cv.string,
    }


def integration_validate_schema(user_input):  # pylint: disable=unused-argument
    """Validate the user input."""
    return {}


async def async_integration_imports(hass, import_data):
    """Do the integration  level import tasks."""
    calendars = import_data["calendars"]
    path = YAML_CALENDARS_FILENAME.format(
        f"_{import_data['data'].get(CONF_ENTITY_NAME)}"
    )
    yaml_filepath = build_yaml_file_path(hass, path)

    for calendar in calendars.values():
        await hass.async_add_executor_job(write_yaml_file, yaml_filepath, calendar)
    return


class MS365OptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options for MS365."""

    def __init__(self, entry: MS365ConfigEntry):
        """Initialize MS365 options flow."""

        self._track_new_calendar = entry.options.get(CONF_TRACK_NEW_CALENDAR, True)
        self._calendars = []
        self._calendar_list = []
        self._calendar_list_selected = []
        self._calendar_list_selected_original = []
        self._yaml_filename = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
        self._yaml_filepath = None
        self._calendar_no = 0
        self._user_input = None

    async def async_step_init(
        self,
        user_input=None,  # pylint: disable=unused-argument
    ) -> FlowResult:
        """Set up the option flow."""

        self._yaml_filepath = build_yaml_file_path(self.hass, self._yaml_filename)
        self._calendars = await self.hass.async_add_executor_job(
            read_calendar_yaml_file,
            self._yaml_filepath,
        )

        for calendar in self._calendars:
            for entity in calendar.get(CONF_ENTITIES):
                self._calendar_list.append(entity[CONF_DEVICE_ID])
                if entity[CONF_TRACK]:
                    self._calendar_list_selected.append(entity[CONF_DEVICE_ID])

        self._calendar_list_selected_original = deepcopy(self._calendar_list_selected)
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input:
            self._user_input = user_input
            self._track_new_calendar = user_input[CONF_TRACK_NEW_CALENDAR]
            self._calendar_list_selected = user_input[CONF_CALENDAR_LIST]

            for calendar in self._calendars:
                for entity in calendar[CONF_ENTITIES]:
                    entity[CONF_TRACK] = (
                        entity[CONF_DEVICE_ID] in self._calendar_list_selected
                    )

            return await self.async_step_calendar_config()

        return self.async_show_form(
            step_id="user",
            description_placeholders={
                CONF_ENTITY_NAME: self.config_entry.data[CONF_ENTITY_NAME]
            },
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CALENDAR_LIST, default=self._calendar_list_selected
                    ): cv.multi_select(self._calendar_list),
                    vol.Optional(
                        CONF_TRACK_NEW_CALENDAR,
                        default=self._track_new_calendar,
                    ): BOOLEAN_SELECTOR,
                }
            ),
            errors=errors,
            last_step=False,
        )

    async def async_step_calendar_config(self, user_input=None) -> FlowResult:
        """Handle calendar setup."""
        if user_input is not None:
            for calendar in self._calendars:
                for entity in calendar[CONF_ENTITIES]:
                    if (
                        entity[CONF_DEVICE_ID]
                        == self._calendar_list_selected[self._calendar_no - 1]
                    ):
                        add_attribute_to_item(entity, user_input, CONF_NAME)
                        add_attribute_to_item(
                            entity, user_input, CONF_HOURS_FORWARD_TO_GET
                        )
                        add_attribute_to_item(
                            entity, user_input, CONF_HOURS_BACKWARD_TO_GET
                        )
                        add_attribute_to_item(entity, user_input, CONF_MAX_RESULTS)
                        add_attribute_to_item(
                            entity, user_input, CONF_SENSITIVITY_EXCLUDE
                        )
                        return await self.async_step_calendar_config()

        if self._calendar_no == len(self._calendar_list_selected):
            return await self._async_tidy_up(self._user_input)

        calendar_item = self._get_calendar_item()
        last_step = self._calendar_no == len(self._calendar_list_selected)
        return self.async_show_form(
            step_id="calendar_config",
            description_placeholders={
                CONF_ENTITY_NAME: self.config_entry.data[CONF_ENTITY_NAME],
                CONF_DEVICE_ID: calendar_item[CONF_DEVICE_ID],
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=calendar_item[CONF_NAME],
                    ): cv.string,
                    vol.Required(
                        CONF_HOURS_FORWARD_TO_GET,
                        default=calendar_item[CONF_HOURS_FORWARD_TO_GET],
                    ): int,
                    vol.Required(
                        CONF_HOURS_BACKWARD_TO_GET,
                        default=calendar_item[CONF_HOURS_BACKWARD_TO_GET],
                    ): int,
                    vol.Optional(
                        CONF_MAX_RESULTS,
                        description={
                            "suggested_value": calendar_item.get(CONF_MAX_RESULTS)
                        },
                    ): cv.positive_int,
                }
            ),
            last_step=last_step,
        )

    def _get_calendar_item(self):
        self._calendar_no += 1
        for calendar in self._calendars:
            for entity in calendar[CONF_ENTITIES]:
                if (
                    entity[CONF_DEVICE_ID]
                    == self._calendar_list_selected[self._calendar_no - 1]
                ):
                    return entity

    async def _async_tidy_up(self, user_input):
        await self.hass.async_add_executor_job(
            write_calendar_yaml_file, self._yaml_filepath, self._calendars
        )
        for calendar in self._calendar_list_selected_original:
            if calendar not in self._calendar_list_selected:
                await self._async_delete_calendar(calendar)
        update = self.async_create_entry(title="", data=user_input)
        await self.hass.config_entries.async_reload(self._config_entry_id)
        return update

    async def _async_delete_calendar(self, calendar):
        entity_id = build_calendar_entity_id(
            calendar, self.config_entry.data[CONF_ENTITY_NAME]
        )
        ent_reg = entity_registry.async_get(self.hass)
        entities = entity_registry.async_entries_for_config_entry(
            ent_reg, self._config_entry_id
        )
        for entity in entities:
            if entity.entity_id == entity_id:
                ent_reg.async_remove(entity_id)
                return
