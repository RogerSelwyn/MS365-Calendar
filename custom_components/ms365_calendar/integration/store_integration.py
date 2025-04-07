"""MS365 Calendar local storage."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const_integration import DOMAIN
from .sync.store import CalendarStore

STORAGE_KEY_FORMAT = "{domain}.Storage-{entry_id}"
STORAGE_VERSION = 1
# Buffer writes every few minutes (plus guaranteed to be written at shutdown)
STORAGE_SAVE_DELAY_SECONDS = 120

_LOGGER = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):
    """Encoder for serialising an event"""

    def default(self, o):
        attributes = {}

        if not hasattr(o, "__dict__"):
            return
        for k, v in vars(o).items():
            key = _beautify_key(k)
            if key not in [
                "con",
                "protocol",
                "main_resource",
                "untrack",
            ] and not key.startswith("_"):
                if isinstance(v, datetime):
                    val = str(v)
                elif hasattr(v, "value"):
                    val = v.value
                else:
                    val = v
                attributes[key] = val

        return attributes


def _beautify_key(key):
    index = key.find("__")
    return key if index <= 0 else key[index + 2 :]


class LocalCalendarStore(CalendarStore):
    """Storage for local persistence of calendar and event data."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize LocalCalendarStore."""
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            STORAGE_KEY_FORMAT.format(domain=DOMAIN, entry_id=entry_id),
            private=True,
            encoder=JSONEncoder,
        )
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> dict[str, Any] | None:
        """Load data."""
        if self._data is None:
            _LOGGER.debug("Load from store")
            self._data = await self._store.async_load() or {}
        return self._data

    async def async_save(self, data: dict[str, Any]) -> None:
        """Save data."""
        self._data = data

        def provide_data() -> dict:
            _LOGGER.debug("Delayed save data")

            return data

        self._store.async_delay_save(provide_data, STORAGE_SAVE_DELAY_SECONDS)

    async def async_remove(self) -> None:
        """Remove data."""
        await self._store.async_remove()
