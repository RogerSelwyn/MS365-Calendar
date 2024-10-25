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

from .helpers.const import UPDATE_CALENDAR_LIST
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.mocks import MS365MOCKS
from .helpers.utils import check_entity_state


async def test_full_init(
    hass: HomeAssistant,
    base_config_entry: MS365MockConfigEntry,
    base_token,
    requests_mock: Mocker,
    entity_registry: er.EntityRegistry,
):
    """Test full MS365 initialisation."""
    MS365MOCKS.standard_mocks(requests_mock)

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    assert hasattr(base_config_entry.runtime_data, "options")
    check_entity_state(hass, "calendar.test_calendar1", "on")
    check_entity_state(hass, "calendar.test_calendar2", "off")

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == 2


async def test_reload(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test for reload."""

    result = await hass.config_entries.options.async_init(base_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TRACK_NEW_CALENDAR: True,
            CONF_CALENDAR_LIST: UPDATE_CALENDAR_LIST,
        },
    )
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload"
    ) as mock_async_reload:
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "Calendar1",
                CONF_HOURS_FORWARD_TO_GET: 24,
                CONF_HOURS_BACKWARD_TO_GET: 0,
            },
        )
    assert mock_async_reload.called


async def test_invalid_client_1(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test an invalid client."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)

    with patch(
        "O365.Account.get_current_user",
        side_effect=InvalidClientError(description="client secret expired"),
    ):
        await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()
    assert "Client Secret expired for account" in caplog.text


async def test_invalid_client_2(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test an invalid client."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)

    with patch(
        "O365.Account.get_current_user",
        side_effect=InvalidClientError(description="token error"),
    ):
        await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()
    assert "Token error for account" in caplog.text
