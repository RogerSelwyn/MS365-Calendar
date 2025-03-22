import asyncio
import functools as ft
import logging
from collections.abc import Generator, Iterable
from datetime import datetime, time, timedelta, timezone
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from ical.iter import (
    MergedIterable,
    SortableItem,
    SortableItemTimeline,
    SortableItemValue,
    SortedItemIterable,
)
from ical.timespan import Timespan
from O365.calendar import Event  # pylint: disable=no-name-in-module)
from requests.exceptions import HTTPError, RetryError

from .store_integration import CalendarStore, InMemoryCalendarStore, ScopedCalendarStore
from .utils_integration import add_call_data_to_event, get_end_date, get_start_date

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=7)
# Maximum number of upcoming events to consider for state changes between
# coordinator updates.
MAX_UPCOMING_EVENTS = 20
SYNC_EVENT_MIN_TIME = timedelta(days=-60)
SYNC_EVENT_MAX_TIME = timedelta(days=90)

from .const_integration import CONST_GROUP, EVENT_SYNC, ITEMS


class M365CalendarService:
    """Calendar service interface to M365.
    The `M365CalendarService` is the primary API service for this library. It supports
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
        """Init the M365 Calendar service."""
        self.hass = hass
        self.calendar_id = calendar_id
        self._account = account
        self.group_calendar = calendar_id.startswith(CONST_GROUP)
        self._sensitivity_exclude = sensitivity_exclude
        self._limit = 999
        self._search = search

    async def async_calendar_init(self):
        if self.group_calendar:
            self._schedule = None
            self.calendar = await self.hass.async_add_executor_job(
                ft.partial(self._account.schedule, resource=self.calendar_id)
            )
        else:
            self._schedule = await self.hass.async_add_executor_job(self._account.schedule)
            try:
                self.calendar = await self.hass.async_add_executor_job(
                    ft.partial(self._schedule.get_calendar, calendar_id=self.calendar_id)
                )
                return True
            except (HTTPError, RetryError, ConnectionError) as err:
                _LOGGER.warning("Error getting calendar events - %s", err)
                return False

    async def async_get_event(self, event_id: str) -> Event:
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
            _LOGGER.warning("Error getting calendar events - %s", err)
            return None

    async def async_create_event(self, subject, start, end, **kwargs) -> Event:        
        event = self.calendar.new_event()
        event = add_call_data_to_event(event, subject, start, end, **kwargs)
        await self.hass.async_add_executor_job(event.save)
        return event

    async def async_patch_event(self, event_id, subject, start, end, **kwargs) -> None:
        """Updates an event using patch semantics, with raw API data."""
        event = await self.async_get_event(event_id)
        event = add_call_data_to_event(event, subject, start, end, **kwargs)
        await self.hass.async_add_executor_job(event.save)

    async def async_delete_event(self, event_id: str,) -> None:
        """Delete an event on the specified calendar."""
        event = await self.async_get_event(event_id)
        await self.hass.async_add_executor_job(event.delete)

class M365Timeline(SortableItemTimeline[Event]):
    """A set of events on a calendar.
    A timeline is created by the local sync API and not instantiated directly.
    """

    def __init__(self, iterable: Iterable[SortableItem[Timespan, Event]]) -> None:
        super().__init__(iterable)

def timespan_of(event: Event, tzinfo: datetime.tzinfo) -> Timespan:
        """Return a timespan representing the event start and end."""
        if tzinfo is None:
            tzinfo = datetime.timezone.utc
        return Timespan.of(
            normalize(event.start, tzinfo),
            normalize(event.end, tzinfo),
        )


def calendar_timeline(
    events: list[Event], tzinfo: datetime.tzinfo
) -> M365Timeline:
    """Create a timeline for events on a calendar, including recurrence."""
    normal_events: list[Event] = []
    for event in events:
        normal_events.append(event)

    def sortable_items() -> Generator[SortableItem[Timespan, Event], None, None]:
        nonlocal normal_events
        for event in normal_events:
            _LOGGER
            yield SortableItemValue(timespan_of(event, tzinfo), event)

    iters: list[Iterable[SortableItem[Timespan, Event]]] = []
    iters.append(SortedItemIterable(sortable_items, tzinfo))

    return M365Timeline(MergedIterable(iters))

def normalize(date, tzinfo: datetime.tzinfo) -> datetime:
        """Convert date or datetime to a value that can be used for comparison."""
        value = date
        if not isinstance(value, datetime):
            value = datetime.combine(value, time.min)
        if value.tzinfo is None:
            value = value.replace(tzinfo=(tzinfo if tzinfo else datetime.timezone.utc))
        return value

class M365CalendarEventStoreService:
    """Performs event lookups from the local store.
    A CalendarEventStoreService should not be instantiated directly, and
    instead created from a `gcal_sync.sync.CalendarEventSyncManager`.
    """

    def __init__(
        self,
        store: CalendarStore,
        calendar_id: str,
        api: M365CalendarService,
    ) -> None:
        """Initialize CalendarEventStoreService."""
        self._store = store
        self._calendar_id = calendar_id
        self._api = api

    async def async_list_events(
        self, start_date, end_date
    ) :
        """Return the set of events matching the criteria."""

        timeline = await self.async_get_timeline(dt_util.get_default_time_zone())

        events=list(
            timeline.overlapping(
                start_date,
                end_date,
            )
        )
        return events

    async def async_get_timeline(
        self, tzinfo: datetime.tzinfo
    ) -> M365Timeline:
        """Get the timeline of events."""
        if tzinfo is None:
            tzinfo = datetime.timezone.utc
        events_data = await self._lookup_events_data()
        _LOGGER.debug("Created timeline of %d events", len(events_data))

        def _build_timeline() -> M365Timeline:
            """Build the timeline of events, which can take some time to parse."""
            _LOGGER.debug(f"Building timeline of with events {events_data}")
            event_objects = [cast(Event, data) for data in events_data.values()]
            return calendar_timeline(event_objects, tzinfo)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _build_timeline)

    async def async_add_event(self, subject, start, end, **kwargs) -> None:
        """Add the specified event to the calendar.
        You should sync the event store after adding an event.
        """
        _LOGGER.debug("Adding event: %s", subject)
        await self._api.async_create_event(subject, start, end, **kwargs)

    async def async_delete_event(
        self, event_id
    ) -> None:
        """Delete the event from the calendar.
        This method is used to delete an existing event. For a recurring event
        either the whole event or instances of an event may be deleted.
        """

        _LOGGER.debug("Deleting event: %s", event_id)
        await self._api.async_delete_event(event_id)

    async def _lookup_events_data(self) -> dict[str, Any]:
        """Loookup the raw events storage dictionary."""
        store_data = await self._store.async_load() or {}
        store_data.setdefault(ITEMS, {})
        return store_data.get(ITEMS, {})  # type: ignore[no-any-return]

class M365CalendarEventSyncManager:
    """Manages synchronizing events from API to local store."""

    def __init__(
        self,
        api: M365CalendarService,
        calendar_id: str | None = None,
        store: CalendarStore | None = None,
    ) -> None:
        """Initialize CalendarEventSyncManager."""
        self._api = api
        self._calendar_id = calendar_id
        self._store = (
            ScopedCalendarStore(
                ScopedCalendarStore(store, EVENT_SYNC), self._calendar_id
            )
            if store
            else InMemoryCalendarStore()
        )

    @property
    def store_service(self) -> M365CalendarEventStoreService:
        """Return the local API for fetching events."""
        return M365CalendarEventStoreService(self._store, self._calendar_id, self._api)

    @property
    def api(self) -> M365CalendarService:
        """Return the cloud API."""
        return self._api

    async def async_list_events(
        self, start_date, end_date
    ) :
        """Return the set of events matching the criteria."""

        events = await self._api.async_list_events(start_date, end_date)
        return events

    def _items_func(self, events) -> dict[str, Any]:
        items = {}
        for item in events:
            if not item.object_id:
                continue
            items[item.object_id] = item
        return items

    async def run(self) -> None:
        """Run the event sync manager."""
        _LOGGER.debug("Syncing Calendar Events: %s", self._calendar_id)
        store_data = await self._store.async_load() or {}
        new_data = await self._api.async_list_events(start_date= dt_util.now() + SYNC_EVENT_MIN_TIME, end_date= dt_util.now() + SYNC_EVENT_MAX_TIME)
        store_data.setdefault(ITEMS, {})
        store_data[ITEMS] = self._items_func(new_data)
        await self._store.async_save(store_data)

class M365CalendarSyncCoordinator(DataUpdateCoordinator):
    """Coordinator for calendar RPC calls that use an efficient sync."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        sync: M365CalendarEventSyncManager,
        name: str,
    ) -> None:
        """Create the CalendarSyncUpdateCoordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=name,
            update_interval=MIN_TIME_BETWEEN_UPDATES,
        )
        self.sync = sync
        self._upcoming_timeline: M365Timeline | None = None

    async def _async_update_data(self) -> M365Timeline:
        """Fetch data from API endpoint."""
        try:
            await self.sync.run()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        timeline = await self.sync.store_service.async_get_timeline(
            dt_util.get_default_time_zone()
        )
        self._upcoming_timeline = timeline
        return timeline

    async def async_get_events(
        self, start_date: datetime, end_date: datetime
    ) -> Iterable[Event]:
        """Get all events in a specific time frame."""
        if not self.data:
            raise HomeAssistantError(
                "Unable to get events: Sync from server has not completed"
            )

        """If the request is for outside of the sync'ed data, manually request it now, will not cache it though"""
        if start_date < dt_util.now() + SYNC_EVENT_MIN_TIME or end_date > dt_util.now() + SYNC_EVENT_MAX_TIME:
            events = await self.sync.store_service.async_list_events(start_date, end_date)
            return events
        return self.data.overlapping(
            start_date,
            end_date,
        )
    
    def get_current_event(self):
        if not self.data:
            _LOGGER.debug(
                "No current event found for %s",
                self.sync._calendar_id,
            )
            self.event = None
            return
        today = datetime.now(timezone.utc)
        events = self.data.overlapping(
            today,
            today + timedelta(days=1),
        )
        
        started_event = None
        not_started_event = None
        all_day_event = None
        for event in events:
            if event.is_all_day:
                if not all_day_event and not self.is_finished(event):
                    all_day_event = event
                continue
            if self.is_started(event) and not self.is_finished(event):
                if not started_event:
                    started_event = event
                continue
            if (
                not self.is_finished(event)
                and not event.is_all_day
                and not not_started_event
            ):
                not_started_event = event

        vevent = None
        if started_event:
            vevent = started_event
        elif all_day_event:
            vevent = all_day_event
        elif not_started_event:
            vevent = not_started_event

        return vevent
    
    @staticmethod
    def is_started(vevent):
        """Is it over."""
        return dt_util.utcnow() >= M365CalendarSyncCoordinator.to_datetime(get_start_date(vevent))

    @staticmethod
    def is_finished(vevent):
        """Is it over."""
        return dt_util.utcnow() >= M365CalendarSyncCoordinator.to_datetime(get_end_date(vevent))
    
    @staticmethod
    def to_datetime(obj):
        """To datetime."""
        if not isinstance(obj, datetime):
            date_obj = dt_util.start_of_local_day(
                dt_util.dt.datetime.combine(obj, dt_util.dt.time.min)
            )
        else:
            date_obj = obj

        return dt_util.as_utc(date_obj)

    @property
    def upcoming(self) -> Iterable[Event] | None:
        """Return upcoming events if any."""
        if self._upcoming_timeline:
            return self._upcoming_timeline.active_after(dt_util.now())
        return None