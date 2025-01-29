"""MS365 Config Entry Structure."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry

MS365ConfigEntry = ConfigEntry["MS365Data"]


@dataclass
class MS365Data:
    """Data previously stored in hass.data."""

    permissions: any
    account: any
    is_authenticated: bool
    coordinator: any
    sensors: any
    options: MappingProxyType[str, Any]
