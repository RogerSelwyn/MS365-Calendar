# pylint: disable=unused-argument, line-too-long
"""Test the diagnostics."""
from copy import deepcopy
from homeassistant.core import HomeAssistant

from .const import ENTITY_NAME
from .helpers.mock_config_entry import MS365MockConfigEntry
from .integration import async_get_config_entry_diagnostics
from .integration.const_integration import (
    BASE_CONFIG_ENTRY,
    DIAGNOSTIC_GRANTED_PERMISSIONS,
    DIAGNOSTIC_REQUESTED_PERMISSIONS,
    DOMAIN,
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


async def test_diagnostics_tenant_id(
    hass: HomeAssistant,
    setup_base_integration: None,
    base_config_entry: MS365MockConfigEntry,
):
    """Test Diagnostics redact the tenant id."""
    data = deepcopy(BASE_CONFIG_ENTRY)
    data["api_options"]["tenant_id"] = "11111111-2222-3333-4444-555555555555"
    entry = MS365MockConfigEntry(domain=DOMAIN, title=ENTITY_NAME, data=data)
    entry.runtime_data = base_config_entry.runtime_data

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["config_entry_data"]["api_options"] == {
        "country": "Default",
        "tenant_id": "**REDACTED**",
    }