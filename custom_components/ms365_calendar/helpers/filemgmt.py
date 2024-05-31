"""File management processes."""

import logging
import os

import yaml
from homeassistant.const import CONF_NAME
from voluptuous.error import Error as VoluptuousError

from ..const import (
    CONF_ACCOUNT_NAME,
    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_TRACK,
    MS365_STORAGE,
    YAML_CALENDARS_FILENAME,
)
from ..schema import YAML_CALENDAR_DEVICE_SCHEMA
from .config_entry import MS365ConfigEntry

_LOGGER = logging.getLogger(__name__)


def load_yaml_file(path, item_id, item_schema):
    """Load the ms365 yaml file."""
    items = {}
    try:
        with open(path, encoding="utf8") as file:
            data = yaml.safe_load(file)
            if data is None:
                return {}
            for item in data:
                try:
                    items[item[item_id]] = item_schema(item)
                except VoluptuousError as exception:
                    # keep going
                    _LOGGER.warning("Invalid Data: %s", exception)
    except FileNotFoundError:
        # When YAML file could not be loaded/did not contain a dict
        return {}

    return items


def _write_yaml_file(yaml_filepath, cal):
    with open(yaml_filepath, "a", encoding="UTF8") as out:
        out.write("\n")
        yaml.dump([cal], out, default_flow_style=False, encoding="UTF8")
        out.close()


def _get_calendar_info(calendar, track_new_devices):
    """Convert data from MS365 into DEVICE_SCHEMA."""
    return YAML_CALENDAR_DEVICE_SCHEMA(
        {
            CONF_CAL_ID: calendar.calendar_id,
            CONF_ENTITIES: [
                {
                    CONF_TRACK: track_new_devices,
                    CONF_NAME: calendar.name,
                    CONF_DEVICE_ID: calendar.name,
                }
            ],
        }
    )


async def async_update_calendar_file(
    entry: MS365ConfigEntry, calendar, hass, track_new_devices
):
    """Update the calendar file."""
    path = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
    yaml_filepath = build_config_file_path(hass, path)
    existing_calendars = await hass.async_add_executor_job(
        load_yaml_file, yaml_filepath, CONF_CAL_ID, YAML_CALENDAR_DEVICE_SCHEMA
    )
    cal = _get_calendar_info(calendar, track_new_devices)
    if cal[CONF_CAL_ID] in existing_calendars:
        return
    await hass.async_add_executor_job(_write_yaml_file, yaml_filepath, cal)


def build_config_file_path(hass, filepath):
    """Create config path."""
    root = hass.config.config_dir

    return os.path.join(root, MS365_STORAGE, filepath)


def build_yaml_filename(conf: MS365ConfigEntry, filename):
    """Create the token file name."""

    return filename.format(f"_{conf.data.get(CONF_ACCOUNT_NAME)}")


def read_calendar_yaml_file(yaml_filepath):
    """Read the yaml file."""
    with open(yaml_filepath, encoding="utf8") as file:
        return yaml.safe_load(file)


def write_calendar_yaml_file(yaml_filepath, contents):
    """Write the yaml file."""
    with open(yaml_filepath, "w", encoding="UTF8") as out:
        yaml.dump(contents, out, default_flow_style=False, encoding="UTF8")
