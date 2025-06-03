"""Calendar coordinator processing."""

import logging
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from O365.calendar import Event  # pylint: disable=no-name-in-module)

from .const_integration import (
    CONF_ADVANCED_OPTIONS,
    CONF_DAYS_BACKWARD,
    CONF_DAYS_FORWARD,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DAYS_BACKWARD,
    DEFAULT_DAYS_FORWARD,
    DEFAULT_UPDATE_INTERVAL,
)
from .sync.sync import MS365CalendarEventSyncManager
from .sync.timeline import MS365Timeline
from .utils_integration import get_end_date, get_start_date

_LOGGER = logging.getLogger(__name__)
# Maximum number of upcoming events to consider for state changes between
# coordinator updates.
# MAX_UPCOMING_EVENTS = 20


class MS365CalendarSyncCoordinator(DataUpdateCoordinator):
    """Coordinator for calendar RPC calls that use an efficient sync."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        sync: MS365CalendarEventSyncManager,
        name: str,
        entity,
    ) -> None:
        """Create the CalendarSyncUpdateCoordinator."""
        update_interval = entry.options.get(CONF_ADVANCED_OPTIONS, {}).get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=name,
            update_interval=timedelta(seconds=update_interval),
        )
        days_backward = entry.options.get(CONF_ADVANCED_OPTIONS, {}).get(
            CONF_DAYS_BACKWARD, DEFAULT_DAYS_BACKWARD
        )
        days_forward = entry.options.get(CONF_ADVANCED_OPTIONS, {}).get(
            CONF_DAYS_FORWARD, DEFAULT_DAYS_FORWARD
        )
        self.sync = sync
        # self._upcoming_timeline: MS365Timeline | None = None
        self.event = None
        self._sync_event_min_time = timedelta(
            days=(min(entity.get(CONF_HOURS_BACKWARD_TO_GET) / 24, days_backward))
        )
        self._sync_event_max_time = timedelta(
            days=(max(entity.get(CONF_HOURS_FORWARD_TO_GET) / 24, days_forward))
        )
        self._last_sync_min = None
        self._last_sync_max = None
        self.entity = entity

    async def _async_update_data(self) -> MS365Timeline:
        """Fetch data from API endpoint."""
        _LOGGER.debug("Started fetching %s data", self.name)

        self._last_sync_min = dt_util.now() + self._sync_event_min_time
        self._last_sync_max = dt_util.now() + self._sync_event_max_time
        await self.sync.run(self._last_sync_min, self._last_sync_max)

        return await self.sync.store_service.async_get_timeline(
            dt_util.get_default_time_zone()
        )
        # self._upcoming_timeline = timeline
        # return timeline

    async def async_get_events(
        self, start_date: datetime, end_date: datetime
    ) -> Iterable[Event]:
        """Get all events in a specific time frame."""
        if not self.data:
            raise HomeAssistantError(
                "Unable to get events: Sync from server has not completed"
            )

        # If the request is for outside of the synced data, manually request it now,
        # will not cache it though
        if start_date < self._last_sync_min or end_date > self._last_sync_max:
            _LOGGER.debug(
                "Fetch events from api - %s - %s - %s", self.name, start_date, end_date
            )
            return await self.sync.async_list_events(start_date, end_date)
        else:
            _LOGGER.debug(
                "Fetch events from cache - %s - %s - %s",
                self.name,
                start_date,
                end_date,
            )

            return self.data.overlapping(
                start_date,
                end_date,
            )

    def get_current_event(self):
        """Get the current event."""
        if not self.data:
            _LOGGER.debug(
                "No current event found for %s",
                self.sync.calendar_id,
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
        return dt_util.utcnow() >= MS365CalendarSyncCoordinator.to_datetime(
            get_start_date(vevent)
        )

    @staticmethod
    def is_finished(vevent):
        """Is it over."""
        return dt_util.utcnow() >= MS365CalendarSyncCoordinator.to_datetime(
            get_end_date(vevent)
        )

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
