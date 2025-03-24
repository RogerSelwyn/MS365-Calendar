"""Library for handling local event sync."""

import logging
from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from ..const_integration import EVENT_SYNC, ITEMS
from .api import MS365CalendarEventStoreService, MS365CalendarService
from .store import CalendarStore, ScopedCalendarStore

SYNC_EVENT_MIN_TIME = timedelta(days=-60)
SYNC_EVENT_MAX_TIME = timedelta(days=90)
_LOGGER = logging.getLogger(__name__)


class MS365CalendarEventSyncManager:
    """Manages synchronizing events from API to local store."""

    def __init__(
        self,
        api: MS365CalendarService,
        calendar_id: str | None = None,
        store: CalendarStore | None = None,
    ) -> None:
        """Initialize CalendarEventSyncManager."""
        self._api = api
        self.calendar_id = calendar_id
        self._store = ScopedCalendarStore(
            ScopedCalendarStore(store, EVENT_SYNC), self.calendar_id
        )

    @property
    def store_service(self) -> MS365CalendarEventStoreService:
        """Return the local API for fetching events."""
        return MS365CalendarEventStoreService(self._store, self.calendar_id, self._api)

    @property
    def api(self) -> MS365CalendarService:
        """Return the cloud API."""
        return self._api

    async def async_list_events(self, start_date, end_date):
        """Return the set of events matching the criteria."""
        return await self._api.async_list_events(start_date, end_date)

    async def run(self) -> None:
        """Run the event sync manager."""
        # _LOGGER.debug("Syncing Calendar Events: %s", self.calendar_id)
        store_data = await self._store.async_load() or {}
        new_data = await self.async_list_events(
            start_date=dt_util.now() + SYNC_EVENT_MIN_TIME,
            end_date=dt_util.now() + SYNC_EVENT_MAX_TIME,
        )
        store_data.setdefault(ITEMS, {})
        store_data[ITEMS] = _items_func(new_data)
        await self._store.async_save(store_data)


def _items_func(events) -> dict[str, Any]:
    items = {}
    for item in events:
        if not item.object_id:
            continue
        items[item.object_id] = item
    return items
