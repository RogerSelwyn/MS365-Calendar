"""Diagnostics support for MS365."""

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from ..classes.config_entry import MS365ConfigEntry
from .const_integration import CONF_CAL_ID, CONST_GROUP, YAML_CALENDARS_FILENAME
from .filemgmt_integration import (
    build_yaml_file_path,
    build_yaml_filename,
    load_yaml_file,
)
from .schema_integration import YAML_CALENDAR_DEVICE_SCHEMA

TO_REDACT = {CONF_CAL_ID}


async def async_integration_diagnostics(hass: HomeAssistant, entry: MS365ConfigEntry):
    """Get integration specific diagnostics."""
    yaml_filename = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
    yaml_filepath = build_yaml_file_path(hass, yaml_filename)
    calendars = await hass.async_add_executor_job(
        load_yaml_file, yaml_filepath, CONF_CAL_ID, YAML_CALENDAR_DEVICE_SCHEMA
    )

    redacted_calendars = {}
    for i, key in enumerate(calendars.keys(), start=1):
        group = CONST_GROUP if key.startswith(CONST_GROUP) else ""
        redacted_calendars[f"**{group}REDACTED{i}**"] = calendars[key]
    return async_redact_data(redacted_calendars, TO_REDACT)
