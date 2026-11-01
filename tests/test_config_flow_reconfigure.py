# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

from unittest.mock import patch

import pytest
from requests_mock import Mocker

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir

from .const import BASE_CONFIG_ENTRY, CLIENT_ID, ENTITY_NAME, RECONFIGURE_CONFIG_ENTRY, TENANT_OPTIONS, TOKEN_URL_ASSERT
from .helpers.mock_config_entry import MS365MockConfigEntry, config_entry_setup
from .helpers.utils import build_token_url, mock_token, token_filename, token_setup
from .integration.const_integration import AUTH_CALLBACK_PATH_DEFAULT, BASE_TOKEN_PERMS, DOMAIN, MS365ConfigFlow
from .integration.helpers_integration.mocks import MS365MOCKS


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
    assert result["description_placeholders"]["auth_url"].startswith(f"{TOKEN_URL_ASSERT}{CLIENT_ID}")
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
    changed_input = config_entry_setup(RECONFIGURE_CONFIG_ENTRY, base_attributes={"client_secret": "9999"})

    with patch.object(
        hass.config_entries,
        "async_reload",
        wraps=hass.config_entries.async_reload,
    ) as reload:
        await _async_reconfigure(hass, requests_mock, base_config_entry)
        assert reload.call_count == 1
        assert base_config_entry.state is ConfigEntryState.LOADED

        await _async_reconfigure(hass, requests_mock, base_config_entry, user_input=changed_input)
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
    assert [issue.translation_key for issue in issue_registry.issues.values()] == ["corrupted"]
    token_file = token_filename(tmp_path)
    assert token_file.is_file()

    await _async_reconfigure(hass, requests_mock, base_config_entry, token_file=token_file)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert not issue_registry.issues


async def test_reconfigure_outdated_token(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
    legacy_token,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test reconfigure replaces an outdated token and clears its repair issue."""
    await _async_setup_failed_entry(hass, requests_mock, base_config_entry)
    assert [issue.translation_key for issue in issue_registry.issues.values()] == ["outdated"]
    token_file = token_filename(tmp_path)
    assert token_file.is_file()

    await _async_reconfigure(hass, requests_mock, base_config_entry, token_file=token_file)

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
        data=config_entry_setup(BASE_CONFIG_ENTRY, base_attributes={"entity_name": "other"}),
        version=MS365ConfigFlow.VERSION,
        minor_version=MS365ConfigFlow.MINOR_VERSION,
    )
    other_entry.add_to_hass(hass)
    await _async_setup_failed_entry(hass, requests_mock, base_config_entry)
    assert other_entry.state is ConfigEntryState.SETUP_ERROR
    assert len(issue_registry.issues) == 2

    await _async_reconfigure(hass, requests_mock, base_config_entry)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert list(issue_registry.issues) == [(DOMAIN, f"missing_{other_entry.entry_id}")]


async def _async_reconfigure(hass, requests_mock, entry, user_input=RECONFIGURE_CONFIG_ENTRY, token_file=None):
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

    if token_file:
        # The unreadable token is gone before the user authorizes
        assert not token_file.is_file()

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


async def _async_setup_failed_entry(hass, requests_mock, entry):
    """Set up an entry whose token cannot be used."""
    MS365MOCKS.standard_mocks(requests_mock)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
