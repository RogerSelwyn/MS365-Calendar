"""Diagnostics support for HomeLINK."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant

from .const import CONF_SHARED_MAILBOX
from .helpers.config_entry import MS365ConfigEntry

TO_REDACT = {CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_SHARED_MAILBOX}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    entry: MS365ConfigEntry,
) -> dict:
    """Return diagnostics for a config entry."""
    return {
        "config_entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "config_entry_options": dict(entry.runtime_data.options),
        "config_granted_permissions": list(entry.runtime_data.permissions.permissions),
        "config_requested_permissions": list(
            entry.runtime_data.permissions.requested_permissions
        ),
    }
