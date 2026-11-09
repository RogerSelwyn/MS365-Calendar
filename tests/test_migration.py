# pylint: disable=unused-argument
"""Test migration."""

import pytest
from requests_mock import Mocker

from homeassistant.core import HomeAssistant

from .const import ENTITY_NAME
from .helpers.mock_config_entry import MS365MockConfigEntry
from .integration.const_integration import DOMAIN


async def test_migrate_v1_v2(
    tmp_path,
    hass: HomeAssistant,
    v1_config_entry: MS365MockConfigEntry,
    legacy_token,
    requests_mock: Mocker,
    caplog: pytest.LogCaptureFixture,
):
    """Test v1 migrate."""

    v1_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(v1_config_entry.entry_id)
    assert f"Token {DOMAIN}_{ENTITY_NAME}.token has been deleted" in caplog.text
    assert "Could not locate token at" in caplog.text
