"""Items that relate to gcal_sync.api"""

import functools as ft
import logging
from datetime import datetime
from typing import Any, cast

from homeassistant.core import HomeAssistant
from O365.calendar import Event  # pylint: disable=no-name-in-module)
from requests.exceptions import HTTPError, RetryError

from ..const_integration import CONST_GROUP, ITEMS, EventResponse
from ..utils_integration import add_call_data_to_event
from .store import CalendarStore
from .timeline import MS365Timeline, calendar_timeline

_LOGGER = logging.getLogger(__name__)


class MS365CalendarService:
    """Calendar service interface to MS365.
    The `MS365CalendarService` is the primary API service for this library. It supports
    operations like listing events.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        account,
        calendar_id,
        sensitivity_exclude,
        search,
    ) -> None:
        """Init the MS365 Calendar service."""
        self.hass = hass
        self.calendar_id = calendar_id
        self._schedule = None
        self.calendar = None
        self._account = account
        self.group_calendar = calendar_id.startswith(CONST_GROUP)
        self._sensitivity_exclude = sensitivity_exclude
        self._limit = 999
        self._search = search
        self._error = False

    async def async_calendar_init(self):
        """Async init of calendar data."""
        if self.group_calendar:
            self._schedule = None
            self.calendar = await self.hass.async_add_executor_job(
                ft.partial(self._account.schedule, resource=self.calendar_id)
            )
        else:
            self._schedule = await self.hass.async_add_executor_job(
                self._account.schedule
            )
            try:
                self.calendar = await self.hass.async_add_executor_job(
                    ft.partial(
                        self._schedule.get_calendar, calendar_id=self.calendar_id
                    )
                )
                return True
            except (HTTPError, RetryError, ConnectionError) as err:
                _LOGGER.warning(
                    "Error getting calendar - %s, %s - %s",
                    self._account,
                    self.calendar,
                    err,
                )
                return False

    async def async_get_event(self, event_id: str) -> Event:
        """Get specific event."""
        return await self.hass.async_add_executor_job(self.calendar.get_event, event_id)

    async def async_list_events(self, start_date, end_date):
        """Get the events for the calendar."""

        query = await self.hass.async_add_executor_job(self.calendar.new_query)
        query = query.select(
            "subject",
            "body",
            "start",
            "end",
            "is_all_day",
            "location",
            "categories",
            "sensitivity",
            "show_as",
            "attendees",
            "series_master_id",
            "is_reminder_on",
            "reminderMinutesBeforeStart",
        )
        query = query.on_attribute("start").greater_equal(start_date)
        query.chain("and").on_attribute("end").less_equal(end_date)
        if self._search is not None:
            query.chain("and").on_attribute("subject").contains(self._search)
        # As at March 2023 not contains is not supported by Graph API
        # if self._exclude is not None:
        #     query.chain("and").on_attribute("subject").negate().contains(self._exclude)
        if self._sensitivity_exclude is not None:
            for item in self._sensitivity_exclude:
                query.chain("and").on_attribute("sensitivity").unequal(item.value)
        try:
            return await self.hass.async_add_executor_job(
                ft.partial(
                    self.calendar.get_events,
                    limit=self._limit,
                    query=query,
                    include_recurring=True,
                )
            )
        except (HTTPError, RetryError, ConnectionError) as err:
            self._log_error("Error getting calendar events for data", err)
            return None

    async def async_create_event(self, subject, start, end, **kwargs) -> Event:
        """Add a new event to calendar."""
        event = self.calendar.new_event()
        event = add_call_data_to_event(event, subject, start, end, **kwargs)
        await self.hass.async_add_executor_job(event.save)
        return event

    async def async_patch_event(self, event_id, subject, start, end, **kwargs) -> None:
        """Updates an event using patch semantics, with raw API data."""
        event = await self.async_get_event(event_id)
        event = add_call_data_to_event(event, subject, start, end, **kwargs)
        await self.hass.async_add_executor_job(event.save)

    async def async_delete_event(
        self,
        event_id: str,
    ) -> None:
        """Delete an event on the specified calendar."""
        event = await self.async_get_event(event_id)
        await self.hass.async_add_executor_job(event.delete)

    async def async_send_response(self, event_id, response, send_response, message):
        """Respond to calendar event."""
        event = await self.async_get_event(event_id)
        if response == EventResponse.Accept:
            await self.hass.async_add_executor_job(
                ft.partial(event.accept_event, message, send_response=send_response)
            )

        elif response == EventResponse.Tentative:
            await self.hass.async_add_executor_job(
                ft.partial(
                    event.accept_event,
                    message,
                    tentatively=True,
                    send_response=send_response,
                )
            )

        elif response == EventResponse.Decline:
            await self.hass.async_add_executor_job(
                ft.partial(event.decline_event, message, send_response=send_response)
            )

    def _log_error(self, error, err):
        if not self._error:
            _LOGGER.warning("%s - %s", error, err)
            self._error = True
        else:
            _LOGGER.debug("Repeat error - %s - %s", error, err)


class MS365CalendarEventStoreService:
    """Performs event lookups from the local store.

    A CalendarEventStoreService should not be instantiated directly, and
    instead created from a `gcal_sync.sync.CalendarEventSyncManager`.
    (Relates to gcal_sync.api.CalendarEventStoreService)
    """

    def __init__(
        self,
        store: CalendarStore,
        calendar_id: str,
        api: MS365CalendarService,
    ) -> None:
        """Initialize CalendarEventStoreService."""
        self._store = store
        self._calendar_id = calendar_id
        self._api = api

    # async def async_list_events(self, start_date, end_date):
    #     """Return the set of events matching the criteria."""

    #     timeline = await self.async_get_timeline(dt_util.get_default_time_zone())

    #     events = list(
    #         timeline.overlapping(
    #             start_date,
    #             end_date,
    #         )
    #     )
    #     return events

    async def async_get_timeline(self, tzinfo: datetime.tzinfo) -> MS365Timeline:
        """Get the timeline of events."""
        events_data = await self._lookup_events_data()
        _LOGGER.debug("Created timeline of %s events", len(events_data))

        return await self._async_build_timeline(events_data, tzinfo)

    async def _async_build_timeline(self, events_data, tzinfo) -> MS365Timeline:
        """Build the timeline of events, which can take some time to parse."""
        event_objects = [cast(Event, data) for data in events_data.values()]
        return calendar_timeline(event_objects, tzinfo)

    async def async_add_event(self, subject, start, end, **kwargs) -> None:
        """Add the specified event to the calendar.
        You should sync the event store after adding an event.
        """
        # Should be adding to the event store I believe
        _LOGGER.debug("Adding event: %s", subject)
        return await self._api.async_create_event(subject, start, end, **kwargs)

    async def async_delete_event(self, event_id) -> None:
        """Delete the event from the calendar.
        This method is used to delete an existing event. For a recurring event
        either the whole event or instances of an event may be deleted.
        """
        # Should be deleting from the event store I believe
        _LOGGER.debug("Deleting event: %s", event_id)
        await self._api.async_delete_event(event_id)

    async def _lookup_events_data(self) -> dict[str, Any]:
        """Lookup the raw events storage dictionary."""
        store_data = await self._store.async_load() or {}
        store_data.setdefault(ITEMS, {})
        return store_data.get(ITEMS, {})  # type: ignore[no-any-return]
