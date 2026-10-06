"""Calendar file management processes."""

import logging
import os

from voluptuous.error import Error as VoluptuousError
import yaml

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from ..classes.config_entry import MS365ConfigEntry
from ..const import CONF_ENTITY_NAME
from ..helpers.filemgmt import build_config_file_path
from .const_integration import (
    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_TRACK,
    CONST_GROUP,
    YAML_CALENDARS_FILENAME,
)
from .schema_integration import YAML_CALENDAR_DEVICE_SCHEMA

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
                    _LOGGER.warning(
                        "Invalid Data - duplicate entries may be created in file %s: %s",
                        path,
                        exception,
                    )
    except FileNotFoundError:
        # When YAML file could not be loaded/did not contain a dict
        return {}

    return items


def write_yaml_file(yaml_filepath, cal):
    """Write to the calendar file."""
    dirpath = os.path.dirname(yaml_filepath)
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath)  # pragma: no cover
    missing_newline = _ends_without_newline(yaml_filepath)
    with open(yaml_filepath, "a", encoding="UTF8") as out:
        # A hand edited file may not end with a newline, which would join the
        # new calendar onto its last line
        if missing_newline:
            out.write("\n")
        yaml.safe_dump([cal], out, default_flow_style=False, encoding="UTF8")
        out.close()


def _ends_without_newline(path):
    try:
        with open(path, "rb") as file:
            if file.seek(0, os.SEEK_END) == 0:
                return False
            file.seek(-1, os.SEEK_END)
            return file.read(1) != b"\n"
    except FileNotFoundError:
        return False


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
    entry: MS365ConfigEntry, calendar, hass: HomeAssistant, track_new_devices
):
    """Update the calendar file."""
    path = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
    yaml_filepath = build_yaml_file_path(hass, path)
    existing_calendars = await hass.async_add_executor_job(
        load_yaml_file, yaml_filepath, CONF_CAL_ID, YAML_CALENDAR_DEVICE_SCHEMA
    )
    cal = _get_calendar_info(calendar, track_new_devices)
    if cal[CONF_CAL_ID] in existing_calendars:
        return
    await hass.async_add_executor_job(write_yaml_file, yaml_filepath, cal)


async def async_check_for_deleted_calendars(
    entry: MS365ConfigEntry, calendars, hass: HomeAssistant
):
    """Delete removed calendars from yaml file."""
    if not calendars:
        # Every account has a calendar, so an empty list means the scan failed
        _LOGGER.warning("No calendars found, so none deleted from yaml file")
        return []

    path = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
    yaml_filepath = build_yaml_file_path(hass, path)
    existing_calendars = await hass.async_add_executor_job(
        load_yaml_file, yaml_filepath, CONF_CAL_ID, YAML_CALENDAR_DEVICE_SCHEMA
    )
    calendar_ids = {calendar.calendar_id for calendar in calendars}
    deleted_calendars = []
    for e_cal_id in existing_calendars:
        if e_cal_id.startswith(CONST_GROUP) or e_cal_id in calendar_ids:
            continue
        _LOGGER.info("Calendar deleted from %s: %s", path, e_cal_id)

        deleted_calendars.append(existing_calendars[e_cal_id])
    if deleted_calendars:
        # Rewrite the file as written, not as validated, which holds O365 objects
        deleted_ids = {calendar[CONF_CAL_ID] for calendar in deleted_calendars}
        raw_calendars = await hass.async_add_executor_job(
            read_calendar_yaml_file, yaml_filepath
        )
        await hass.async_add_executor_job(
            write_calendar_yaml_file,
            yaml_filepath,
            [cal for cal in raw_calendars if cal.get(CONF_CAL_ID) not in deleted_ids],
        )
    return deleted_calendars


def build_yaml_filename(conf: MS365ConfigEntry, filename):
    """Create the token file name."""

    return filename.format(f"_{conf.data.get(CONF_ENTITY_NAME)}")


def build_yaml_file_path(hass: HomeAssistant, yaml_filename):
    """Create yaml path."""
    return build_config_file_path(hass, yaml_filename)


def read_calendar_yaml_file(yaml_filepath):
    """Read the yaml file, with no calendars if it is missing or empty."""
    try:
        with open(yaml_filepath, encoding="utf8") as file:
            return yaml.safe_load(file) or []
    except FileNotFoundError:
        return []


def write_calendar_yaml_file(yaml_filepath, contents):
    """Write the yaml file."""
    with open(yaml_filepath, "w", encoding="UTF8") as out:
        yaml.safe_dump(contents, out, default_flow_style=False, encoding="UTF8")
