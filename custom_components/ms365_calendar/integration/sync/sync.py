"""Library for handling local event sync."""

import logging
import re

from ..const_integration import EVENT_SYNC, ITEMS
from .api import MS365CalendarEventStoreService, MS365CalendarService
from .store import CalendarStore, ScopedCalendarStore

_LOGGER = logging.getLogger(__name__)


class MS365CalendarEventSyncManager:
    """Manages synchronizing events from API to local store."""

    def __init__(
        self,
        api: MS365CalendarService,
        calendar_id: str | None = None,
        store: CalendarStore | None = None,
        exclude: list | None = None,
    ) -> None:
        """Initialize CalendarEventSyncManager."""
        self._api = api
        self.calendar_id = calendar_id
        self._store = ScopedCalendarStore(
            ScopedCalendarStore(store, EVENT_SYNC), self.calendar_id
        )
        self._exclude = exclude

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
        events = await self._api.async_list_events(start_date, end_date)

        return self._filter_events(list(events))

    def _filter_events(self, events):
        if not events or not self._exclude:
            return events

        rtn_events = []
        for event in events:
            include = True
            for exclude in self._exclude:
                if re.search(exclude, event.subject):
                    include = False
            if include:
                rtn_events.append(event)

        return rtn_events

    async def run(self, start_date, end_date) -> None:
        """Run the event sync manager."""
        # store_data = await self._store.async_load() or {}
        new_data = await self.async_list_events(
            start_date=start_date,
            end_date=end_date,
        )

        # store_data[ITEMS].update(_add_update_func(store_data, new_data))
        items = {item.object_id: item for item in new_data}
        store_data = {ITEMS: items}
        await self._store.async_save(store_data)


# def _add_update_func(store_data, new_data) -> dict[str, Any]:
#     items = {}
#     for item in new_data:
#         items[item.object_id] = item
#     for key, value in store_data[ITEMS].items():
#         if key not in items and isinstance(value, dict):
#             items[key] = DictObj(value)
#     return items


# class DictObj:
#     """To convert from dict to object."""

#     def __init__(self, in_dict: dict):
#         assert isinstance(in_dict, dict)
#         for key, val in in_dict.items():
#             if isinstance(val, (list, tuple)):
#                 setattr(
#                     self, key, [DictObj(x) if isinstance(x, dict) else x for x in val]
#                 )
#             elif key in ["start", "end"]:
#                 setattr(self, key, parser.parse(val))
#             elif key in ["location"]:
#                 setattr(self, key, val)
#             elif key in ["sensitivity"]:
#                 setattr(self, key, EventSensitivity(val))
#             elif key in ["show_as"]:
#                 setattr(self, key, EventShowAs(val))
#             elif key in ["importance"]:
#                 setattr(self, key, ImportanceLevel(val))
#             else:
#                 setattr(self, key, DictObj(val) if isinstance(val, dict) else val)
