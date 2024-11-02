# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from requests_mock import Mocker

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_CALENDAR_LIST,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_TRACK_NEW_CALENDAR,
)

from ..helpers.mock_config_entry import MS365MockConfigEntry
from ..helpers.utils import get_schema_default
from .const import UPDATE_CALENDAR_LIST
from .helpers.mocks import MS365MOCKS


async def test_options_flow(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the options flow"""

    result = await hass.config_entries.options.async_init(base_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    schema = result["data_schema"].schema
    assert get_schema_default(schema, CONF_TRACK_NEW_CALENDAR) is True
    assert get_schema_default(schema, CONF_CALENDAR_LIST) == ["Calendar1", "Calendar2"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TRACK_NEW_CALENDAR: False,
            CONF_CALENDAR_LIST: UPDATE_CALENDAR_LIST,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "calendar_config"
    assert result["last_step"] is True
    schema = result["data_schema"].schema
    assert get_schema_default(schema, CONF_NAME) == "Calendar1"
    assert get_schema_default(schema, CONF_HOURS_FORWARD_TO_GET) == 24
    assert get_schema_default(schema, CONF_HOURS_BACKWARD_TO_GET) == 0
    assert get_schema_default(schema, CONF_MAX_RESULTS) is None

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Calendar1_Changed",
            CONF_HOURS_FORWARD_TO_GET: 48,
            CONF_HOURS_BACKWARD_TO_GET: -48,
            CONF_MAX_RESULTS: 5,
        },
    )
    assert result.get("type") is FlowResultType.CREATE_ENTRY
    assert "result" in result
    assert result["result"] is True

    assert result["data"][CONF_TRACK_NEW_CALENDAR] is False

    assert result["data"][CONF_CALENDAR_LIST] == UPDATE_CALENDAR_LIST


@pytest.mark.parametrize(
    "base_config_entry",
    [{"basic_calendar": True, "enable_update": True}],
    indirect=True,
)
async def test_invalid_entry(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for invalid config mix."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        "'enable_update' should not be true when 'basic_calendar' is true"
        in caplog.text
    )