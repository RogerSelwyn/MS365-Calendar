"""Do configuration setup."""

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from requests.exceptions import HTTPError

from ..classes.config_entry import MS365ConfigEntry
from ..const import CONF_ENTITY_NAME
from .const_integration import (
    CONF_CAL_ID,
    CONF_CAN_EDIT,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_ENTITY,
    CONF_EXCLUDE,
    CONF_SEARCH,
    CONF_SENSITIVITY_EXCLUDE,
    CONF_TRACK,
    PLATFORMS,
    YAML_CALENDARS_FILENAME,
)
from .coordinator_integration import (
    MS365CalendarSyncCoordinator,
)
from .filemgmt_integration import (
    build_yaml_file_path,
    build_yaml_filename,
    load_yaml_file,
)
from .schema_integration import YAML_CALENDAR_DEVICE_SCHEMA
from .store_integration import LocalCalendarStore
from .sync.api import MS365CalendarService, async_scan_for_calendars
from .sync.store import ScopedCalendarStore
from .sync.sync import (
    MS365CalendarEventSyncManager,
)
from .utils_integration import build_calendar_entity_id

_LOGGER = logging.getLogger(__name__)


async def async_do_setup(hass: HomeAssistant, entry: ConfigEntry, account):
    """Run the setup after we have everything configured."""

    scanned_calendars = await async_scan_for_calendars(hass, entry, account)
    coordinators, keys = await _async_setup_coordinators(
        hass,
        account,
        entry,
        scanned_calendars,
    )

    return coordinators, keys, PLATFORMS


async def async_integration_remove_entry(hass: HomeAssistant, entry: MS365ConfigEntry):
    """Integration specific entry removal."""
    yaml_filename = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
    yaml_filepath = build_yaml_file_path(hass, yaml_filename)
    if os.path.exists(yaml_filepath):
        await hass.async_add_executor_job(os.remove, yaml_filepath)
    store = LocalCalendarStore(hass, entry.entry_id)
    await store.async_remove()


async def _async_setup_coordinators(
    hass,
    account,
    entry: MS365ConfigEntry,
    scanned_calendars,
):
    yaml_filename = build_yaml_filename(entry, YAML_CALENDARS_FILENAME)
    yaml_filepath = build_yaml_file_path(hass, yaml_filename)
    calendars = await hass.async_add_executor_job(
        load_yaml_file, yaml_filepath, CONF_CAL_ID, YAML_CALENDAR_DEVICE_SCHEMA
    )

    local_store = LocalCalendarStore(hass, entry.entry_id)

    coordinators = []
    keys = []
    for cal_id, calendar in calendars.items():
        for entity in calendar.get(CONF_ENTITIES):
            if not entity[CONF_TRACK]:
                continue
            can_edit = next(
                (
                    scanned_calendar.can_edit
                    for scanned_calendar in scanned_calendars
                    if scanned_calendar.calendar_id == cal_id
                ),
                True,
            )
            entity_id = build_calendar_entity_id(
                entity.get(CONF_DEVICE_ID), entry.data[CONF_ENTITY_NAME]
            )

            keys.append(
                {
                    CONF_ENTITY: entity,
                    CONF_ENTITY_ID: entity_id,
                    CONF_CAN_EDIT: can_edit,
                }
            )
            try:
                api = MS365CalendarService(
                    hass,
                    account,
                    cal_id,
                    entity.get(CONF_SENSITIVITY_EXCLUDE),
                    entity.get(CONF_SEARCH),
                )
                await api.async_calendar_init()
                unique_id = f"{entity.get(CONF_NAME)}"
                sync_manager = MS365CalendarEventSyncManager(
                    api,
                    cal_id,
                    store=ScopedCalendarStore(local_store, unique_id),
                    exclude=entity.get(CONF_EXCLUDE),
                )
                coordinators.append(
                    MS365CalendarSyncCoordinator(
                        hass, entry, sync_manager, unique_id, entity
                    )
                )
            except HTTPError:
                _LOGGER.warning(
                    "No permission for calendar, please remove - Name: %s; Device: %s;",
                    entity[CONF_NAME],
                    entity[CONF_DEVICE_ID],
                )
                continue

    return coordinators, keys
