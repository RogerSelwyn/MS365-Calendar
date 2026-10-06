# pylint: disable=unused-argument
"""Test migration."""

from copy import deepcopy

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from requests_mock import Mocker

from .const import ENTITY_NAME
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import mock_token
from .integration.const_integration import (
    BASE_CONFIG_ENTRY,
    BASE_TOKEN_PERMS,
    DOMAIN,
    MIGRATION_CONFIG_ENTRY,
    MS365ConfigFlow,
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


async def test_duplicate_migration_renamed_entry(
    hass: HomeAssistant,
    base_config_entry: MS365MockConfigEntry,
):
    """Test import finds an entry that has been renamed."""
    base_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(base_config_entry, title="Renamed")

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MIGRATION_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert hass.config_entries.async_entries(DOMAIN) == [base_config_entry]


async def test_migration_title_only_match(
    hass: HomeAssistant,
):
    """Test import is not blocked by an entry that only has the same title."""
    other_entry = MS365MockConfigEntry(
        domain=DOMAIN,
        title=ENTITY_NAME,
        data=deepcopy(BASE_CONFIG_ENTRY) | {"entity_name": "other"},
        version=MS365ConfigFlow.VERSION,
        minor_version=MS365ConfigFlow.MINOR_VERSION,
    )
    other_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MIGRATION_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data["entity_name"] == ENTITY_NAME
    assert len(hass.config_entries.async_entries(DOMAIN)) == 2


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
