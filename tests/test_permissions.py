# pylint: disable=unused-argument, line-too-long
"""Test permission handling."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import token_setup
from .integration.const_integration import DOMAIN, ENTITY_NAME


async def test_no_token(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test no token."""
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Could not locate token" in caplog.text
    assert len(issue_registry.issues) == 1


async def test_corrupt_token(
    tmp_path,
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Fixture for setting up the component."""
    token_setup(tmp_path, "corrupt")
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        f"Token file corrupted for integration '{DOMAIN}', unique identifier '{ENTITY_NAME}', please delete token, re-configure and re-authenticate - No permissions"
        in caplog.text
    )
    assert len(issue_registry.issues) == 1


async def test_corrupt_token2(
    tmp_path,
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Fixture for setting up the component."""
    token_setup(tmp_path, "corrupt2")
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        f"Token file corrupted for integration '{DOMAIN}', unique identifier '{ENTITY_NAME}', please delete token, re-configure and re-authenticate - Expecting value: line 1 column 1 (char 0)"
        in caplog.text
    )
    assert len(issue_registry.issues) == 1
