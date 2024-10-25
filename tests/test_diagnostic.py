# pylint: disable=unused-argument, line-too-long
"""Test odds and sods."""

from homeassistant.core import HomeAssistant

from custom_components.ms365_calendar.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .helpers.mock_config_entry import MS365MockConfigEntry


async def test_diagnostics(
    hass: HomeAssistant,
    setup_base_integration: None,
    base_config_entry: MS365MockConfigEntry,
):
    """Test Diagnostics."""
    result = await async_get_config_entry_diagnostics(hass, base_config_entry)
    print(result)

    assert "config_entry_data" in result
    assert result["config_entry_data"]["client_id"] == "**REDACTED**"
    assert result["config_entry_data"]["client_secret"] == "**REDACTED**"
    assert result["config_granted_permissions"] == [
        "Calendars.Read",
        "User.Read",
        "profile",
        "openid",
        "email",
    ]
    assert result["config_requested_permissions"] == [
        "offline_access",
        "User.Read",
        "Calendars.Read",
    ]
