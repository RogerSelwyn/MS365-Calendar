# pylint: disable=unused-argument
"""Test setup process."""

from unittest.mock import patch

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from oauthlib.oauth2.rfc6749.errors import InvalidClientError
from requests_mock import Mocker

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_CALENDAR_LIST,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_TRACK_NEW_CALENDAR,
)

from .conftest import MS365MockConfigEntry, standard_mocks
from .helpers.const import UPDATE_CALENDAR_LIST
from .helpers.utils import build_token_file, check_entity_state, token_setup


async def test_base_permissions(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the reconfigure flow."""
    assert "Calendars.Read" in base_config_entry.runtime_data.permissions.permissions


async def test_no_token(
    hass: HomeAssistant,
    storage_path_setup,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Fixture for setting up the component."""
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Could not locate token" in caplog.text


async def test_corrupt_token(
    hass: HomeAssistant,
    storage_path_setup,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Fixture for setting up the component."""
    token_setup("corrupt")
    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Token corrupted for integration" in caplog.text


async def test_missing_permissions(
    hass: HomeAssistant,
    base_config_entry: MS365MockConfigEntry,
    storage_path_setup,
    caplog: pytest.LogCaptureFixture,
):
    """Test full MS365 initialisation."""

    build_token_file("")

    base_config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as mock_async_create_issue:
        await hass.config_entries.async_setup(base_config_entry.entry_id)

    assert "Minimum required permissions: 'Calendars.Read'" in caplog.text
    assert mock_async_create_issue.called


async def test_higher_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    update_token,
    storage_path_setup,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Fixture for setting up the component."""
    standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == 2


async def test_shared_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    shared_token,
    storage_path_setup,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Fixture for setting up the component."""
    standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == 2
