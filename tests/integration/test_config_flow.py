# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

from copy import deepcopy
from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from requests_mock import Mocker

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_ADVANCED_OPTIONS,
    CONF_CALENDAR_LIST,
    CONF_DAYS_BACKWARD,
    CONF_DAYS_FORWARD,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_TRACK_NEW_CALENDAR,
    CONF_UPDATE_INTERVAL,
    DEFAULT_DAYS_BACKWARD,
    DEFAULT_DAYS_FORWARD,
    DEFAULT_UPDATE_INTERVAL,
)

from ..helpers.mock_config_entry import MS365MockConfigEntry
from ..helpers.utils import build_token_url, get_schema_default, mock_token
from .const_integration import (
    AUTH_CALLBACK_PATH_DEFAULT,
    RECONFIGURE_CONFIG_ENTRY,
    BASE_CONFIG_ENTRY,
    BASE_TOKEN_PERMS,
    DOMAIN,
    SHARED_TOKEN_PERMS,
    UPDATE_CALENDAR_LIST,
)
from .helpers_integration.mocks import MS365MOCKS


async def test_options_flow(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the options flow"""

    result = await hass.config_entries.options.async_init(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    schema = result["data_schema"].schema
    assert get_schema_default(schema, CONF_TRACK_NEW_CALENDAR) is True
    assert get_schema_default(schema, CONF_CALENDAR_LIST) == [
        "Calendar1",
        "Calendar2",
        "Calendar3",
    ]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TRACK_NEW_CALENDAR: False,
            CONF_CALENDAR_LIST: UPDATE_CALENDAR_LIST,
            CONF_ADVANCED_OPTIONS: {
                CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                CONF_DAYS_BACKWARD: DEFAULT_DAYS_BACKWARD,
                CONF_DAYS_FORWARD: DEFAULT_DAYS_FORWARD,
            },
        },
    )
    await hass.async_block_till_done()
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
    await hass.async_block_till_done()
    assert result.get("type") is FlowResultType.CREATE_ENTRY

    assert result["data"][CONF_TRACK_NEW_CALENDAR] is False

    assert result["data"][CONF_CALENDAR_LIST] == UPDATE_CALENDAR_LIST


async def test_invalid_combinations(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the reconfigure flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": base_config_entry.entry_id,
        },
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    reconfigure_config_entry = deepcopy(RECONFIGURE_CONFIG_ENTRY)
    reconfigure_config_entry["basic_calendar"] = True
    reconfigure_config_entry["enable_update"] = True

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=reconfigure_config_entry,
    )

    assert "errors" in result
    assert "basic_calendar" in result["errors"]
    assert result["errors"]["basic_calendar"] == "cannot_have_basic_update"

    reconfigure_config_entry = deepcopy(RECONFIGURE_CONFIG_ENTRY)
    reconfigure_config_entry["basic_calendar"] = True
    reconfigure_config_entry["shared_mailbox"] = "john@nospam.com"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=reconfigure_config_entry,
    )

    assert "errors" in result
    assert "basic_calendar" in result["errors"]
    assert result["errors"]["basic_calendar"] == "cannot_have_basic_shared"

    reconfigure_config_entry = deepcopy(RECONFIGURE_CONFIG_ENTRY)
    reconfigure_config_entry["groups"] = True
    reconfigure_config_entry["shared_mailbox"] = "john@nospam.com"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=reconfigure_config_entry,
    )

    assert "errors" in result
    assert "groups" in result["errors"]
    assert result["errors"]["groups"] == "cannot_have_groups_shared"


async def test_shared_email_invalid(
    hass: HomeAssistant,
    requests_mock: Mocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for invalid shared mailbox."""
    mock_token(requests_mock, SHARED_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    user_input = deepcopy(BASE_CONFIG_ENTRY)
    email = "john@nomail.com"
    user_input["shared_mailbox"] = email
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )

    with patch(
        f"custom_components.{DOMAIN}.classes.api.MS365CustomAccount",
        return_value=mock_account(email),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY

    assert (
        f"Login email address '{email}' should not be entered as shared email address, config attribute removed"
        in caplog.text
    )


def mock_account(email):
    """Mock the account."""
    return MagicMock(is_authenticated=True, username=email, main_resource=email)
