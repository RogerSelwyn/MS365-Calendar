# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

from copy import deepcopy

from aiohttp import web_response
import pytest
from pytest_homeassistant.typing import ClientSessionGenerator
from requests_mock import Mocker

from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .const import CLIENT_ID, ENTITY_NAME, TOKEN_PARAMS, TOKEN_URL_ASSERT, TOKEN_URL_CN21V_ASSERT
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import build_token_url, mock_call, mock_cn21v_token, mock_token, token_setup
from .integration.const_integration import (
    ALT_CONFIG_ENTRY,
    AUTH_CALLBACK_PATH_ALT,
    AUTH_CALLBACK_PATH_DEFAULT,
    BASE_CONFIG_ENTRY,
    BASE_MISSING_PERMS,
    BASE_TOKEN_PERMS,
    COUNTRY_CONFIG_ENTRY,
    DOMAIN,
    URL,
)
from .integration.helpers_integration.mocks import MS365MOCKS


async def test_environment_secret_flow(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    requests_mock: Mocker,
) -> None:
    """Test that the client secret is loaded from the environment."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)
    monkeypatch.setenv("MS365_CLIENT_SECRET", "environment-secret")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    environment_config = {
        **BASE_CONFIG_ENTRY,
        "client_secret_source": "environment",
        "client_secret_env_var": "MS365_CLIENT_SECRET",
        "client_secret": "",
    }
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=environment_config,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data["client_secret_source"] == "environment"
    assert result["result"].data["client_secret_env_var"] == "MS365_CLIENT_SECRET"
    assert "client_secret" not in result["result"].data


async def test_environment_secret_step(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
    requests_mock: Mocker,
) -> None:
    """Test the client secret step shown when the user step has no secret."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)
    monkeypatch.setenv("MS365_CUSTOM_SECRET", "environment-secret")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    user_input = deepcopy(BASE_CONFIG_ENTRY) | {"client_secret_source": "environment"}
    del user_input["client_secret"]
    del user_input["client_secret_env_var"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "client_secret"
    assert not result["errors"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret_env_var": "MS365_NOT_SET"}
    )
    assert result["step_id"] == "client_secret"
    assert result["errors"] == {"client_secret_env_var": "missing_client_secret"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret_env_var": "MS365_CUSTOM_SECRET"}
    )
    assert result["step_id"] == "request_default"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT)},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].data["client_secret_source"] == "environment"
    assert result["result"].data["client_secret_env_var"] == "MS365_CUSTOM_SECRET"
    assert "client_secret" not in result["result"].data


async def test_manual_secret_step_missing_secret(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test the manual secret step rejects an empty secret."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    user_input = deepcopy(BASE_CONFIG_ENTRY)
    del user_input["client_secret"]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )
    assert result["step_id"] == "client_secret"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret": ""}
    )
    assert result["step_id"] == "client_secret"
    assert result["errors"] == {"client_secret": "missing_client_secret"}


async def test_default_flow(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test the default config_flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["auth_url"].startswith(f"{TOKEN_URL_ASSERT}{CLIENT_ID}")
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

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_alt"
    assert result["description_placeholders"]["auth_url"].startswith(f"{TOKEN_URL_ASSERT}{CLIENT_ID}")
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
    mock_cn21v_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.cn21v_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=COUNTRY_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["auth_url"].startswith(f"{TOKEN_URL_CN21V_ASSERT}{CLIENT_ID}")
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

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["auth_url"].startswith(f"{TOKEN_URL_ASSERT}{CLIENT_ID}")
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
    assert result["description_placeholders"]["failed_permissions"] == f"\n\nMissing - {BASE_MISSING_PERMS}"


async def test_missing_permissions_alt_flow(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test missing permissions on the alternate flow."""
    mock_token(requests_mock, "")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_alt"
    assert result["description_placeholders"]["auth_url"].startswith(f"{TOKEN_URL_ASSERT}{CLIENT_ID}")
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
    assert "base" in result["errors"]
    assert result["errors"]["base"] == "permissions"
    assert result["description_placeholders"]["failed_permissions"] == f"\n\nMissing - {BASE_MISSING_PERMS}"


async def test_invalid_token_url(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test invalid token url."""
    mock_call(requests_mock, URL.OPENID, "openid")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

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

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

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

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "client_secret"
    assert "errors" in result
    assert result["errors"]["base"] == "error_authenticating"


async def test_already_configured(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test already configured entity name."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
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

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"entity_name": "already_configured"}


async def test_change_entity_name(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
) -> None:
    """Test a new name can be entered after the first one was already used."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=deepcopy(BASE_CONFIG_ENTRY),
    )
    assert result["step_id"] == "user"
    assert result["errors"] == {"entity_name": "already_configured"}

    user_input = deepcopy(BASE_CONFIG_ENTRY)
    user_input["entity_name"] = "test2"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )
    assert result["step_id"] == "request_default"
    assert result["description_placeholders"]["entity_name"] == "test2"


async def test_token_without_entry(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
) -> None:
    """Test a token left without a config entry does not block adding the account."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )
    assert result["step_id"] == "request_default"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].state is ConfigEntryState.LOADED


async def test_already_configured_without_token(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test an entry without a token still blocks a second entry with its name."""
    mock_call(requests_mock, URL.OPENID, "openid")
    base_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )
    assert result["step_id"] == "user"
    assert result["errors"] == {"entity_name": "already_configured"}


class OtherCallbackView(HomeAssistantView):
    """Callback view of another integration at the same path."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH_ALT
    name = "api:other"

    async def get(self, request):
        """Receive the callback."""
        return web_response.Response(text="other")


async def test_alt_flow_after_abandoned_flow(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test the alternate flow works after an abandoned flow and another view."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
    )
    assert result["step_id"] == "request_alt"
    abandoned_url = build_token_url(result, AUTH_CALLBACK_PATH_ALT)
    hass.config_entries.flow.async_abort(result["flow_id"])
    assert not hass.data.get("ms365_auth_callback")
    # An integration on an older shared core takes over the callback path
    hass.http.register_view(OtherCallbackView())

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
    )
    assert result["step_id"] == "request_alt"

    client = await hass_client()
    await client.get(build_token_url(result, AUTH_CALLBACK_PATH_ALT))
    await client.get(abandoned_url)
    await client.get(f"{AUTH_CALLBACK_PATH_ALT}?{TOKEN_PARAMS.format('unknown')}")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].state is ConfigEntryState.LOADED
    assert hass.data["ms365_auth_callback"] == {}


async def test_alt_flow_no_callback(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test the alternate flow shows an error when no callback was received."""
    mock_call(requests_mock, URL.OPENID, "openid")

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["step_id"] == "request_alt"
    assert result["errors"] == {"base": "invalid_url"}


async def test_unusable_returned_url(
    hass: HomeAssistant,
    requests_mock: Mocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a pasted authorization link, a stale url or an error redirect."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )
    token_url = build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": result["description_placeholders"]["auth_url"]},
    )
    assert result["step_id"] == "request_default"
    assert result["errors"] == {"url": "invalid_url"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": f"{AUTH_CALLBACK_PATH_DEFAULT}?{TOKEN_PARAMS.format('stale')}"},
    )
    assert result["step_id"] == "request_default"
    assert result["errors"] == {"url": "invalid_url"}
    assert "state mismatch" in caplog.text

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": token_url.replace("code=fake.code", "error=access_denied")},
    )
    assert result["step_id"] == "request_default"
    assert result["errors"] == {"url": "token_file_error"}
    assert "access_denied" in caplog.text

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": token_url},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
