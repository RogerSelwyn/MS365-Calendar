# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from requests_mock import Mocker

from .const import (
    CLIENT_ID,
    ENTITY_NAME,
    TOKEN_PARAMS,
    TOKEN_URL_ASSERT,
    TOKEN_URL_CN21V_ASSERT,
)
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import (
    build_token_url,
    mock_call,
    mock_token,
    token_setup,
    mock_cn21v_token,
)
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
    MS365ConfigFlow,
)
from .integration.helpers_integration.mocks import MS365MOCKS

TENANT_OPTIONS = {"api_options": {"country": "Default", "tenant_id": ""}}


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
    mock_cn21v_token(requests_mock, BASE_TOKEN_PERMS)
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
        f"{TOKEN_URL_CN21V_ASSERT}{CLIENT_ID}"
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
    assert "base" in result["errors"]
    assert result["errors"]["base"] == "permissions"
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


async def _async_setup_failed_entry(hass, requests_mock, entry):
    """Set up an entry whose token cannot be used."""
    MS365MOCKS.standard_mocks(requests_mock)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def _async_reconfigure(
    hass, requests_mock, entry, user_input=RECONFIGURE_CONFIG_ENTRY
):
    """Run a successful reconfigure flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=user_input,
    )
    assert result["step_id"] == "request_default"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()


async def test_reconfigure_failed_entry(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test reconfigure loads an entry that failed to set up."""
    await _async_setup_failed_entry(hass, requests_mock, base_config_entry)
    assert len(issue_registry.issues) == 1

    await _async_reconfigure(hass, requests_mock, base_config_entry)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert not issue_registry.issues


@pytest.mark.parametrize("base_config_entry", [TENANT_OPTIONS], indirect=True)
async def test_reconfigure_reloads_once(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test reconfigure reloads a loaded entry once, with or without changes."""
    changed_input = deepcopy(RECONFIGURE_CONFIG_ENTRY)
    changed_input["client_secret"] = "9999"

    with patch.object(
        hass.config_entries,
        "async_reload",
        wraps=hass.config_entries.async_reload,
    ) as reload:
        await _async_reconfigure(hass, requests_mock, base_config_entry)
        assert reload.call_count == 1
        assert base_config_entry.state is ConfigEntryState.LOADED

        await _async_reconfigure(
            hass, requests_mock, base_config_entry, user_input=changed_input
        )
        assert reload.call_count == 2

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert base_config_entry.data["client_secret"] == "9999"


async def test_reconfigure_corrupt_token(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test reconfigure replaces a token that cannot be read."""
    token_setup(tmp_path, "corrupt2")
    await _async_setup_failed_entry(hass, requests_mock, base_config_entry)
    assert [issue.translation_key for issue in issue_registry.issues.values()] == [
        "corrupted"
    ]

    await _async_reconfigure(hass, requests_mock, base_config_entry)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert not issue_registry.issues


async def test_reconfigure_outdated_token(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
    legacy_token,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test reconfigure replaces an outdated token and clears its repair issue."""
    await _async_setup_failed_entry(hass, requests_mock, base_config_entry)
    assert [issue.translation_key for issue in issue_registry.issues.values()] == [
        "outdated"
    ]

    await _async_reconfigure(hass, requests_mock, base_config_entry)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert not issue_registry.issues


async def test_repair_issues_per_entry(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test each entry has its own repair issue and reconfigure clears only its own."""
    other_entry = MS365MockConfigEntry(
        domain=DOMAIN,
        title="other",
        data=deepcopy(BASE_CONFIG_ENTRY) | {"entity_name": "other"},
        version=MS365ConfigFlow.VERSION,
        minor_version=MS365ConfigFlow.MINOR_VERSION,
    )
    other_entry.add_to_hass(hass)
    await _async_setup_failed_entry(hass, requests_mock, base_config_entry)
    assert other_entry.state is ConfigEntryState.SETUP_ERROR
    assert len(issue_registry.issues) == 2

    await _async_reconfigure(hass, requests_mock, base_config_entry)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert list(issue_registry.issues) == [
        (DOMAIN, f"missing_{other_entry.entry_id}")
    ]


async def test_change_entity_name(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
) -> None:
    """Test a new name can be entered after the first one was already used."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
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

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
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

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )
    assert result["step_id"] == "user"
    assert result["errors"] == {"entity_name": "already_configured"}


async def test_alt_flow_after_abandoned_flow(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    requests_mock: Mocker,
) -> None:
    """Test the alternate flow works after an earlier one was abandoned."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=ALT_CONFIG_ENTRY,
    )
    assert result["step_id"] == "request_alt"
    abandoned_url = build_token_url(result, AUTH_CALLBACK_PATH_ALT)
    hass.config_entries.flow.async_abort(result["flow_id"])

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
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


async def test_alt_flow_no_callback(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test the alternate flow shows an error when no callback was received."""
    mock_call(requests_mock, URL.OPENID, "openid")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
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
    """Test a pasted authorization link or a stale url shows an error."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
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
        user_input={
            "url": f"{AUTH_CALLBACK_PATH_DEFAULT}?{TOKEN_PARAMS.format('stale')}"
        },
    )
    assert result["step_id"] == "request_default"
    assert result["errors"] == {"url": "invalid_url"}
    assert "state mismatch" in caplog.text

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": token_url},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
