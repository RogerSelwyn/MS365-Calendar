"""Library for local storage of calendar data. Direct copy of gcal_sync.store."""

from __future__ import annotations

import logging
from abc import ABC
from typing import Any

__all__ = [
    "CalendarStore",
]

_LOGGER = logging.getLogger(__name__)


class CalendarStore(ABC):
    """Interface for external calendar storage.

    This is an abstract class that may be implemented by callers to provide a
    custom implementation for storing the calendar database.
    """

    async def async_load(self) -> dict[str, Any] | None:
        """Load data."""

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save data."""


# class InMemoryCalendarStore(CalendarStore):
#     """An in memory implementation of CalendarStore."""

#     def __init__(self) -> None:
#         self._data: dict[str, Any] | None = None

#     async def async_load(self) -> dict[str, Any] | None:
#         """Load data."""
#         return self._data

#     async def async_save(self, data: dict[str, Any]) -> None:
#         """Save data."""
#         self._data = data


class ScopedCalendarStore(CalendarStore):
    """A store that reads/writes to a key within the store."""

    def __init__(self, store: CalendarStore, key: str) -> None:
        """Initialize ScopedCalendarStore."""
        self._store = store
        self._key = key

    async def async_load(self) -> dict[str, Any]:
        """Load data from the store."""

        store_data = await self._store.async_load() or {}
        return store_data.get(self._key, {})  # type: ignore[no-any-return]

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save data to the store, performing a read/modify/write"""

        store_data = await self._store.async_load() or {}
        store_data[self._key] = data
        return await self._store.async_save(store_data)
