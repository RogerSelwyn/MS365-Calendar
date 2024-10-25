# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

import json
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from requests_mock import Mocker

from custom_components.ms365_calendar.const import (
    AUTH_CALLBACK_PATH_ALT,
    AUTH_CALLBACK_PATH_DEFAULT,
)
from custom_components.ms365_calendar.integration.const_integration import (
    CONF_CALENDAR_LIST,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_TRACK_NEW_CALENDAR,
    DOMAIN,
)

from .helpers.const import (
    CLIENT_ID,
    CLIENT_SECRET,
    ENTITY_NAME,
    TOKEN_URL_ASSERT,
    UPDATE_CALENDAR_LIST,
)
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.mocks import MS365MOCKS
from .helpers.utils import build_token_url, mock_token


async def test_default_flow(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test the default config_flow."""
    mock_token(requests_mock, "Calendars.Read")
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": False,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["auth_url"].startswith(
        f"{TOKEN_URL_ASSERT}{CLIENT_ID}"
    )
    assert result["description_placeholders"]["entity_name"] == ENTITY_NAME
    assert result["description_placeholders"]["failed_permissions"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "result" in result
    assert result["result"].state.value == "loaded"


async def test_alt_flow(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test the alternate config_flow."""
    mock_token(requests_mock, "Calendars.Read")
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": True,
            "enable_update": False,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_alt"
    assert result["description_placeholders"]["auth_url"].startswith(
        f"{TOKEN_URL_ASSERT}{CLIENT_ID}"
    )
    assert result["description_placeholders"]["entity_name"] == ENTITY_NAME
    assert result["description_placeholders"]["failed_permissions"] is None

    client = await hass_client()
    await client.get(build_token_url(result, AUTH_CALLBACK_PATH_ALT))
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "result" in result
    assert result["result"].state.value == "loaded"


async def test_missing_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test missing permissions."""
    mock_token(requests_mock, "Calendars.Read")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": True,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["auth_url"].startswith(
        f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?response_type=code&client_id={CLIENT_ID}"
    )
    assert result["description_placeholders"]["entity_name"] == ENTITY_NAME
    assert result["description_placeholders"]["failed_permissions"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert "errors" in result
    assert "url" in result["errors"]
    assert result["errors"]["url"] == "permissions"
    assert (
        result["description_placeholders"]["failed_permissions"]
        == "\n\nMissing - Calendars.ReadWrite"
    )


async def test_missing_permissions_alt_flow(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test missing permissions on the alternate flow."""
    mock_token(requests_mock, "Calendars.Read")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": True,
            "enable_update": True,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    print(result)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_alt"
    assert result["description_placeholders"]["auth_url"].startswith(
        f"{TOKEN_URL_ASSERT}{CLIENT_ID}"
    )
    assert result["description_placeholders"]["entity_name"] == ENTITY_NAME
    assert result["description_placeholders"]["failed_permissions"] is None

    client = await hass_client()
    await client.get(build_token_url(result, AUTH_CALLBACK_PATH_ALT))
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_alt"
    assert "errors" in result
    assert "url" in result["errors"]
    assert result["errors"]["url"] == "permissions"
    assert (
        result["description_placeholders"]["failed_permissions"]
        == "\n\nMissing - Calendars.ReadWrite"
    )


async def test_invalid_token_url(
    hass: HomeAssistant,
) -> None:
    """Test invalid token url."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": True,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": "https://invalid",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert "errors" in result
    assert "url" in result["errors"]
    assert result["errors"]["url"] == "invalid_url"


async def test_invalid_token(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test invalid token."""
    requests_mock.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        text="corrupted token",
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": False,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert "errors" in result
    assert "url" in result["errors"]
    assert result["errors"]["url"] == "token_file_error"


async def test_json_decode_error(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test error decoding the token."""
    mock_token(requests_mock, "Calendars.Read")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(
        "O365.utils.token.BaseTokenBackend.get_token",
        side_effect=json.decoder.JSONDecodeError("msg", "doc", 1),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "entity_name": ENTITY_NAME,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "alt_auth_method": False,
                "enable_update": False,
                "basic_calendar": False,
                "groups": False,
                "shared_mailbox": "",
            },
        )

    print(result)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "errors" in result
    assert "entity_name" in result["errors"]
    assert result["errors"]["entity_name"] == "error_authenticating"


async def test_already_configured(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test already configured entity name."""
    mock_token(requests_mock, "Calendars.Read")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": False,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "entity_name": ENTITY_NAME,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": False,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "errors" in result
    assert "entity_name" in result["errors"]
    assert result["errors"]["entity_name"] == "already_configured"


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
    assert _get_schema_default(schema, CONF_TRACK_NEW_CALENDAR) is True
    assert _get_schema_default(schema, CONF_CALENDAR_LIST) == ["Calendar1", "Calendar2"]

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
    assert _get_schema_default(schema, CONF_NAME) == "Calendar1"
    assert _get_schema_default(schema, CONF_HOURS_FORWARD_TO_GET) == 24
    assert _get_schema_default(schema, CONF_HOURS_BACKWARD_TO_GET) == 0
    assert _get_schema_default(schema, CONF_MAX_RESULTS) is None

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


async def test_reconfigure_flow(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the reconfigure flow."""
    mock_token(requests_mock, "Calendars.Read")
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": base_config_entry.entry_id,
        },
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "alt_auth_method": False,
            "enable_update": False,
            "basic_calendar": False,
            "groups": False,
            "shared_mailbox": "",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["auth_url"].startswith(
        f"{TOKEN_URL_ASSERT}{CLIENT_ID}"
    )
    assert result["description_placeholders"]["entity_name"] == ENTITY_NAME
    assert result["description_placeholders"]["failed_permissions"] is None

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )
    print(result)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


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


def _get_schema_default(schema, key_name):
    """Iterate schema to find a key."""
    for schema_key in schema:
        if schema_key == key_name:
            try:
                return schema_key.default()
            except TypeError:
                return None
    raise KeyError(f"{key_name} not found in schema")
