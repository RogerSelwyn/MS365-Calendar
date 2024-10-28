# pylint: disable=unused-argument, line-too-long
"""Test permission handling."""

import pytest
from homeassistant.core import HomeAssistant

from .helpers.mock_config_entry import MS365MockConfigEntry


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
