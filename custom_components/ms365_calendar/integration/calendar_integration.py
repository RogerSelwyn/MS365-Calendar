"""Main calendar processing."""

import logging
from copy import deepcopy
from datetime import datetime, timedelta
from operator import attrgetter
from typing import Any, cast

from homeassistant.components.calendar import (
    EVENT_DESCRIPTION,
    EVENT_END,
    EVENT_RRULE,
    EVENT_START,
    EVENT_SUMMARY,
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
    extract_offset,
    is_offset_reached,
)
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from ..classes.config_entry import MS365ConfigEntry
from ..classes.entity import MS365Entity
from ..const import CONF_ENABLE_UPDATE, CONF_ENTITY_NAME, EVENT_HA_EVENT
from ..helpers.utils import clean_html
from .const_integration import (
    ATTR_ALL_DAY,
    ATTR_COLOR,
    ATTR_DATA,
    ATTR_EVENT_ID,
    ATTR_HEX_COLOR,
    ATTR_OFFSET,
    CONF_CAN_EDIT,
    CONF_DEVICE_ID,
    CONF_ENTITY,
    CONF_EXCLUDE,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    DEFAULT_OFFSET,
    DOMAIN,
    EVENT_CREATE_CALENDAR_EVENT,
    EVENT_MODIFY_CALENDAR_EVENT,
    EVENT_MODIFY_CALENDAR_RECURRENCES,
    EVENT_REMOVE_CALENDAR_EVENT,
    EVENT_REMOVE_CALENDAR_RECURRENCES,
    EVENT_RESPOND_CALENDAR_EVENT,
    PERM_CALENDARS_READWRITE,
)
from .coordinator_integration import (
    MS365CalendarSyncCoordinator,
)
from .schema_integration import (
    CALENDAR_SERVICE_CREATE_SCHEMA,
    CALENDAR_SERVICE_MODIFY_SCHEMA,
    CALENDAR_SERVICE_REMOVE_SCHEMA,
    CALENDAR_SERVICE_RESPOND_SCHEMA,
)
from .utils_integration import (
    format_event_data,
    get_end_date,
    get_hass_date,
)

_LOGGER = logging.getLogger(__name__)


async def async_integration_setup_entry(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    entry: MS365ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MS365 platform."""

    config_update_supported = bool(
        entry.data[CONF_ENABLE_UPDATE]
        and entry.runtime_data.permissions.validate_authorization(
            PERM_CALENDARS_READWRITE
        )
    )

    for key in entry.runtime_data.sensors:
        entity_id = key[CONF_ENTITY_ID]
        entity = key[CONF_ENTITY]
        name = entity[CONF_NAME]
        for coordinator in entry.runtime_data.coordinator:
            if name != coordinator.name:
                continue

            calendar_id = coordinator.sync.calendar_id
            can_edit = key[CONF_CAN_EDIT]
            update_supported = config_update_supported and can_edit
            device_id = entity[CONF_DEVICE_ID]
            unique_id = f"{calendar_id}_{entry.data[CONF_ENTITY_NAME]}_{device_id}"
            cal = MS365CalendarEntity(
                coordinator.sync.api,
                coordinator,
                entity,
                entity_id,
                entry,
                update_supported,
                name,
                unique_id,
            )
            async_add_entities([cal], False)
            break

    await _async_setup_register_services(config_update_supported)

    return True


async def _async_setup_register_services(config_update_supported):
    platform = entity_platform.async_get_current_platform()

    if config_update_supported:
        platform.async_register_entity_service(
            "create_calendar_event",
            CALENDAR_SERVICE_CREATE_SCHEMA,
            "async_create_calendar_event",
        )
        platform.async_register_entity_service(
            "modify_calendar_event",
            CALENDAR_SERVICE_MODIFY_SCHEMA,
            "async_modify_calendar_event",
        )
        platform.async_register_entity_service(
            "remove_calendar_event",
            CALENDAR_SERVICE_REMOVE_SCHEMA,
            "async_remove_calendar_event",
        )
        platform.async_register_entity_service(
            "respond_calendar_event",
            CALENDAR_SERVICE_RESPOND_SCHEMA,
            "async_respond_calendar_event",
        )


class MS365CalendarEntity(MS365Entity, CalendarEntity):
    """MS365 Calendar Event Processing."""

    _attr_should_poll = False
    _unrecorded_attributes = frozenset((ATTR_DATA, ATTR_COLOR, ATTR_HEX_COLOR))

    def __init__(
        self,
        api,
        coordinator,
        entity,
        entity_id,
        entry: MS365ConfigEntry,
        update_supported,
        name,
        unique_id,
    ):
        """Initialise the MS365 Calendar Event."""
        super().__init__(coordinator, entry, name, entity_id, unique_id)
        self.api = api
        self._start_offset = entity.get(CONF_HOURS_BACKWARD_TO_GET)
        self._end_offset = entity.get(CONF_HOURS_FORWARD_TO_GET)
        self._event = None
        self.entity_id = entity_id
        self._offset_reached = False
        self._data_attribute = []

        self._update_supported = update_supported
        if self._update_supported:
            self._attr_supported_features = (
                CalendarEntityFeature.CREATE_EVENT
                | CalendarEntityFeature.DELETE_EVENT
                | CalendarEntityFeature.UPDATE_EVENT
            )
        self._max_results = entity.get(CONF_MAX_RESULTS)
        self._error = None
        self.exclude = entity.get(CONF_EXCLUDE)

    @property
    def extra_state_attributes(self):
        """Extra state attributes."""
        attributes = {
            ATTR_DATA: self._data_attribute,
        }
        if hasattr(self.api.calendar, ATTR_COLOR):
            attributes[ATTR_COLOR] = self.api.calendar.color
        if hasattr(self.api.calendar, ATTR_HEX_COLOR) and self.api.calendar.hex_color:
            attributes[ATTR_HEX_COLOR] = self.api.calendar.hex_color
        if self._event:
            attributes[ATTR_ALL_DAY] = (
                self._event.all_day if self._event is not None else False
            )
            attributes[ATTR_OFFSET] = self._offset_reached
        return attributes

    @property
    def event(self):
        """Event property."""
        return self._event

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        self.coordinator.config_entry.async_create_background_task(
            self.hass,
            self.coordinator.async_request_refresh(),
            "mS365.calendar-refresh",
        )

    async def async_get_events(self, hass, start_date, end_date):
        """Get events."""
        _LOGGER.debug("Start get_events for %s", self.name)

        results = await self.coordinator.async_get_events(start_date, end_date)
        events = self._build_calendar_events(results)

        _LOGGER.debug("End get_events for %s", self.name)
        return events

    def _build_calendar_events(self, results):
        event_list = []
        for vevent in results:
            try:
                event_list.append(self._build_calendar_event(vevent))
            except HomeAssistantError as err:
                _LOGGER.warning(
                    "Invalid event found - Error: %s, Event: %s", err, vevent
                )

        return event_list

    def _build_calendar_event(self, vevent):
        event = CalendarEvent(
            get_hass_date(vevent.start, vevent.is_all_day),
            get_hass_date(get_end_date(vevent), vevent.is_all_day),
            vevent.subject,
            clean_html(vevent.body),
            vevent.location["displayName"],
            uid=vevent.object_id,
        )
        if vevent.series_master_id:
            event.recurrence_id = vevent.series_master_id
        return event

    def _sort_events(self, events):
        for event in events:
            event.start_sort = event.start
            if event.is_all_day:
                event.start_sort = dt_util.as_utc(
                    dt_util.start_of_local_day(event.start)
                )

        events.sort(key=attrgetter("start_sort"))

        return events

    def _handle_coordinator_update(self) -> None:
        self._update_status()
        self.async_write_ha_state()

    def _update_status(self):
        """Do the update."""
        _LOGGER.debug("Start update for %s", self.name)

        range_start = dt_util.utcnow() + timedelta(hours=self._start_offset)
        range_end = dt_util.utcnow() + timedelta(hours=self._end_offset)
        self._build_extra_attributes(range_start, range_end)
        self._get_current_event()

        _LOGGER.debug("End update for %s", self.name)

    def _get_current_event(self):
        vevent = self.coordinator.get_current_event()
        if not vevent:
            _LOGGER.debug(
                "No matching event found in the calendar results for %s",
                self.entity_id,
            )
            self._event = None
            return

        self._event = deepcopy(self._build_calendar_event(vevent))
        self._event.summary, offset = extract_offset(
            self._event.summary, DEFAULT_OFFSET
        )
        start = MS365CalendarSyncCoordinator.to_datetime(self._event.start)
        self._offset_reached = is_offset_reached(start, offset)

    def _build_extra_attributes(self, range_start, range_end):
        if self.coordinator.data is not None:
            data_events = [
                event
                for event in self.coordinator.data
                if event.end >= range_start and event.start <= range_end
            ]
            data_events = self._sort_events(data_events)

            data = [format_event_data(event) for event in data_events]
            self._data_attribute = data[: self._max_results]

    async def async_create_event(self, **kwargs: Any) -> None:
        """Add a new event to calendar."""
        start = kwargs[EVENT_START]
        end = kwargs[EVENT_END]
        is_all_day = not isinstance(start, datetime)
        subject = kwargs[EVENT_SUMMARY]
        body = kwargs.get(EVENT_DESCRIPTION)
        rrule = kwargs.get(EVENT_RRULE)
        await self.async_create_calendar_event(
            subject,
            start,
            end,
            body=body,
            is_all_day=is_all_day,
            rrule=rrule,
        )

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Update an event on the calendar."""
        start = event[EVENT_START]
        end = event[EVENT_END]
        is_all_day = not isinstance(start, datetime)
        subject = event[EVENT_SUMMARY]
        body = event.get(EVENT_DESCRIPTION)
        rrule = event.get(EVENT_RRULE)
        await self.async_modify_calendar_event(
            event_id=uid,
            recurrence_id=recurrence_id,
            recurrence_range=recurrence_range,
            subject=subject,
            start=start,
            end=end,
            body=body,
            is_all_day=is_all_day,
            rrule=rrule,
        )

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Delete an event on the calendar."""
        await self.async_remove_calendar_event(uid, recurrence_id, recurrence_range)

    async def async_create_calendar_event(self, subject, start, end, **kwargs):
        """Create the event."""

        self._validate_calendar_permissions()

        event = await cast(
            MS365CalendarSyncCoordinator, self.coordinator
        ).sync.store_service.async_add_event(subject, start, end, **kwargs)

        self._raise_event(EVENT_CREATE_CALENDAR_EVENT, event.object_id)
        await self.coordinator.async_refresh()

    async def async_modify_calendar_event(
        self,
        event_id,
        recurrence_id=None,
        recurrence_range=None,
        subject=None,
        start=None,
        end=None,
        **kwargs,
    ):
        """Modify the event."""

        self._validate_calendar_permissions()

        if self.api.group_calendar:
            _group_calendar_log(self.entity_id)

        if recurrence_range:
            await self._async_update_calendar_event(
                recurrence_id,
                EVENT_MODIFY_CALENDAR_RECURRENCES,
                subject,
                start,
                end,
                **kwargs,
            )
        else:
            await self._async_update_calendar_event(
                event_id, EVENT_MODIFY_CALENDAR_EVENT, subject, start, end, **kwargs
            )
        await self.coordinator.async_refresh()

    async def _async_update_calendar_event(
        self, event_id, ha_event, subject, start, end, **kwargs
    ):
        await self.api.async_patch_event(event_id, subject, start, end, **kwargs)
        self._raise_event(ha_event, event_id)

    async def async_remove_calendar_event(
        self,
        event_id,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ):
        """Remove the event."""
        self._validate_calendar_permissions()

        if self.api.group_calendar:
            _group_calendar_log(self.entity_id)

        if recurrence_range:
            await self._async_delete_calendar_event(
                recurrence_id, EVENT_REMOVE_CALENDAR_RECURRENCES
            )
        else:
            await self._async_delete_calendar_event(
                event_id, EVENT_REMOVE_CALENDAR_EVENT
            )

    async def _async_delete_calendar_event(self, event_id, ha_event):
        await cast(
            MS365CalendarSyncCoordinator, self.coordinator
        ).sync.store_service.async_delete_event(event_id)
        self._raise_event(ha_event, event_id)
        await self.coordinator.async_refresh()

    async def async_respond_calendar_event(
        self, event_id, response, send_response=True, message=None
    ):
        """Respond to calendar event."""
        self._validate_calendar_permissions()

        if self.api.group_calendar:
            _group_calendar_log(self.entity_id)

        await self.api.async_send_response(event_id, response, send_response, message)
        self._raise_event(EVENT_RESPOND_CALENDAR_EVENT, event_id)
        await self.coordinator.async_refresh()

    def _validate_calendar_permissions(self):
        self._validate_permissions(PERM_CALENDARS_READWRITE, PERM_CALENDARS_READWRITE)

        if not self._update_supported:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="calendar_not_editable",
                translation_placeholders={
                    "name": self._name,
                },
            )

        return True

    def _raise_event(self, event_type, event_id):
        self.hass.bus.fire(
            f"{DOMAIN}_{event_type}",
            {ATTR_EVENT_ID: event_id, EVENT_HA_EVENT: True},
        )
        _LOGGER.debug("%s - %s", event_type, event_id)


def _group_calendar_log(entity_id):
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="ms365_group_calendar_error",
        translation_placeholders={
            "entity_id": entity_id,
        },
    )
