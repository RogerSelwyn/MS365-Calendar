# pylint: disable=unused-argument
"""Test migration"""

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from requests_mock import Mocker

from .const import ENTITY_NAME
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import mock_token
from .integration.const_integration import (
    BASE_TOKEN_PERMS,
    DOMAIN,
    MIGRATION_CONFIG_ENTRY,
)
from .integration.helpers_integration.mocks import MS365MOCKS


async def test_default_flow(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the default config_flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MIGRATION_CONFIG_ENTRY,
    )
    assert (
        f"Could not locate token at {tmp_path}/storage/tokens/{DOMAIN}_test.token"
        in caplog.text
    )


async def test_duplicate_migration(
    hass: HomeAssistant,
    setup_base_integration,
    caplog: pytest.LogCaptureFixture,
):
    """Test duplicate import."""

    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MIGRATION_CONFIG_ENTRY,
    )
    assert f"Entry already imported for '{DOMAIN}' - '{ENTITY_NAME}'" in caplog.text


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
