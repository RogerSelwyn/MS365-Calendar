# pylint: disable=unused-argument, line-too-long
"""Test permission handling."""

import pytest
from homeassistant.core import HomeAssistant

from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import token_setup


async def test_no_token(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test no token."""
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Could not locate token" in caplog.text


async def test_corrupt_token(
    tmp_path,
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Fixture for setting up the component."""
    token_setup(tmp_path, "corrupt")
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Token corrupted for integration" in caplog.text
