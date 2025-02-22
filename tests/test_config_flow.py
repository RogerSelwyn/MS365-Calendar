# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from requests_mock import Mocker

from .const import CLIENT_ID, ENTITY_NAME, TOKEN_URL_ASSERT
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import build_token_url, mock_call, mock_token, token_setup
from .integration.const_integration import (
    ALT_CONFIG_ENTRY,
    AUTH_CALLBACK_PATH_ALT,
    AUTH_CALLBACK_PATH_DEFAULT,
    BASE_CONFIG_ENTRY,
    BASE_MISSING_PERMS,
    BASE_TOKEN_PERMS,
    COUNTRY_CONFIG_ENTRY,
    DOMAIN,
    RECONFIGURE_CONFIG_ENTRY,
    URL,
)
from .integration.helpers_integration.mocks import MS365MOCKS


async def test_default_flow(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test the default config_flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
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
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
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


async def test_non_default_country(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test the 21Vianet config_flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.cn21v_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=COUNTRY_CONFIG_ENTRY,
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


async def test_missing_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test missing permissions."""
    mock_token(requests_mock, "")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
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
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert "errors" in result
    assert "url" in result["errors"]
    assert result["errors"]["url"] == "permissions"
    assert (
        result["description_placeholders"]["failed_permissions"]
        == f"\n\nMissing - {BASE_MISSING_PERMS}"
    )


async def test_missing_permissions_alt_flow(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test missing permissions on the alternate flow."""
    mock_token(requests_mock, "")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
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
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_alt"
    assert "errors" in result
    assert "url" in result["errors"]
    assert result["errors"]["url"] == "permissions"
    assert (
        result["description_placeholders"]["failed_permissions"]
        == f"\n\nMissing - {BASE_MISSING_PERMS}"
    )


async def test_invalid_token_url(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test invalid token url."""
    mock_call(requests_mock, URL.OPENID, "openid")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test invalid token."""
    mock_call(requests_mock, URL.OPENID, "openid")
    requests_mock.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        text='{"corrupted": "token"}',
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
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
    assert "Token file retrieval error" in caplog.text


async def test_json_decode_error(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test error decoding the token."""
    token_setup(tmp_path, "corrupt2")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )

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
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
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
        user_input=BASE_CONFIG_ENTRY,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "errors" in result
    assert "entity_name" in result["errors"]
    assert result["errors"]["entity_name"] == "already_configured"


async def test_reconfigure_flow(
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

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=RECONFIGURE_CONFIG_ENTRY,
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

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_legacy_token(
    tmp_path,
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
    legacy_token,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the reconfigure when legacy token exists."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": base_config_entry.entry_id,
        },
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=RECONFIGURE_CONFIG_ENTRY,
    )
    assert "Token no longer valid" in caplog.text
