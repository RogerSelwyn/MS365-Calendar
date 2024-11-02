# pylint: disable=unused-argument, line-too-long
"""Test the diagnostics."""

from homeassistant.core import HomeAssistant

from .helpers.mock_config_entry import MS365MockConfigEntry
from .integration import async_get_config_entry_diagnostics
from .integration.const_integration import (
    DIAGNOSTIC_GRANTED_PERMISSIONS,
    DIAGNOSTIC_REQUESTED_PERMISSIONS,
)


async def test_diagnostics(
    hass: HomeAssistant,
    setup_base_integration: None,
    base_config_entry: MS365MockConfigEntry,
):
    """Test Diagnostics."""
    result = await async_get_config_entry_diagnostics(hass, base_config_entry)

    assert "config_entry_data" in result
    assert result["config_entry_data"]["client_id"] == "**REDACTED**"
    assert result["config_entry_data"]["client_secret"] == "**REDACTED**"
    assert result["config_granted_permissions"] == DIAGNOSTIC_GRANTED_PERMISSIONS
    assert result["config_requested_permissions"] == DIAGNOSTIC_REQUESTED_PERMISSIONS
