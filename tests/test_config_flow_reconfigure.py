# pylint: disable=line-too-long, unused-argument
"""Test the config flow."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from requests_mock import Mocker

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import issue_registry as ir
from homeassistant.core import HomeAssistant
from .integration.helpers_integration.mocks import MS365MOCKS

from .const import (
    CLIENT_ID,
    ENTITY_NAME,
    TOKEN_URL_ASSERT,
    TENANT_OPTIONS,
)
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import (
    build_token_url,
    mock_token,
    token_setup,
    token_filename,
)
from .integration.const_integration import (
    AUTH_CALLBACK_PATH_DEFAULT,
    BASE_CONFIG_ENTRY,
    BASE_TOKEN_PERMS,
    DOMAIN,
    RECONFIGURE_CONFIG_ENTRY,
    MS365ConfigFlow,
)


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
    token_file = token_filename(tmp_path)
    assert token_file.is_file()

    await _async_reconfigure(
        hass, requests_mock, base_config_entry, token_file=token_file
    )

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
    assert [issue.translation_key for issue in issue_registry.issues.values()] == [
        "outdated"
    ]
    token_file = token_filename(tmp_path)
    assert token_file.is_file()

    await _async_reconfigure(
        hass, requests_mock, base_config_entry, token_file=token_file
    )

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
    assert list(issue_registry.issues) == [(DOMAIN, f"missing_{other_entry.entry_id}")]


ENV_VAR = "MS365_CLIENT_SECRET"
ENVIRONMENT_ENTRY_SOURCE = {"client_secret_source": "environment"}
ENVIRONMENT_ENTRY = {
    "client_secret_source": "environment",
    "client_secret_env_var": ENV_VAR,
    "client_secret": "",
}


@pytest.fixture
def environment_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide the client secret through the environment."""
    monkeypatch.setenv(ENV_VAR, "environment-secret")


def _user_input(**overrides):
    """Return the user step input without the client secret fields."""
    user_input = deepcopy(RECONFIGURE_CONFIG_ENTRY)
    del user_input["client_secret"]
    del user_input["client_secret_env_var"]
    return user_input | overrides


async def _async_start_reconfigure(hass, entry, user_input):
    """Start a reconfigure flow and submit the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=user_input
    )


async def _async_finish_reconfigure(hass, result):
    """Authorize the flow and check the reconfigure completes."""
    assert result["step_id"] == "request_default"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT)},
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


def _schema_default(result, key):
    """Return the default of a field in the form schema."""
    return next(k for k in result["data_schema"].schema if k == key).default()


@pytest.mark.parametrize("base_config_entry", [ENVIRONMENT_ENTRY], indirect=True)
async def test_reconfigure_environment_flow(
    environment_secret,
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test reconfigure of an entry using the environment secret."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    result = await _async_start_reconfigure(
        hass, base_config_entry, _user_input(**ENVIRONMENT_ENTRY_SOURCE)
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "client_secret"
    assert not result["errors"]
    assert _schema_default(result, "client_secret_env_var") == ENV_VAR

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret_env_var": ENV_VAR}
    )
    await _async_finish_reconfigure(hass, result)

    assert base_config_entry.state is ConfigEntryState.LOADED
    assert base_config_entry.data["client_secret_source"] == "environment"
    assert base_config_entry.data["client_secret_env_var"] == ENV_VAR
    assert "client_secret" not in base_config_entry.data


@pytest.mark.parametrize("base_config_entry", [ENVIRONMENT_ENTRY], indirect=True)
async def test_reconfigure_environment_default_from_entry(
    environment_secret,
    hass: HomeAssistant,
    requests_mock: Mocker,
    monkeypatch: pytest.MonkeyPatch,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the reconfigure form defaults to the variable already configured."""
    monkeypatch.setenv("OTHER_SECRET", "other-secret")
    hass.config_entries.async_update_entry(
        base_config_entry,
        data=base_config_entry.data | {"client_secret_env_var": "OTHER_SECRET"},
    )
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await _async_start_reconfigure(
        hass, base_config_entry, _user_input(**ENVIRONMENT_ENTRY_SOURCE)
    )

    assert result["step_id"] == "client_secret"
    assert _schema_default(result, "client_secret_env_var") == "OTHER_SECRET"


@pytest.mark.parametrize("base_config_entry", [ENVIRONMENT_ENTRY], indirect=True)
async def test_reconfigure_environment_missing_variable(
    environment_secret,
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test reconfigure reports a variable that is not set, then accepts a valid one."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    result = await _async_start_reconfigure(
        hass, base_config_entry, _user_input(**ENVIRONMENT_ENTRY_SOURCE)
    )
    assert result["step_id"] == "client_secret"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret_env_var": "MS365_NOT_SET"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "client_secret"
    assert result["errors"] == {"client_secret_env_var": "missing_client_secret"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret_env_var": ENV_VAR}
    )
    await _async_finish_reconfigure(hass, result)
    assert base_config_entry.data["client_secret_env_var"] == ENV_VAR


async def test_reconfigure_manual_to_environment(
    environment_secret,
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test switching a manual entry to the environment secret."""
    assert base_config_entry.data["client_secret"] == "5678"
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await _async_start_reconfigure(
        hass, base_config_entry, _user_input(**ENVIRONMENT_ENTRY_SOURCE)
    )
    assert result["step_id"] == "client_secret"
    assert _schema_default(result, "client_secret_env_var") == ENV_VAR

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret_env_var": ENV_VAR}
    )
    await _async_finish_reconfigure(hass, result)

    assert base_config_entry.data["client_secret_source"] == "environment"
    assert base_config_entry.data["client_secret_env_var"] == ENV_VAR
    assert "client_secret" not in base_config_entry.data


@pytest.mark.parametrize("base_config_entry", [ENVIRONMENT_ENTRY], indirect=True)
async def test_reconfigure_environment_to_manual(
    environment_secret,
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test switching an environment entry back to a manual secret."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)

    result = await _async_start_reconfigure(
        hass, base_config_entry, _user_input(client_secret_source="manual")
    )
    assert result["step_id"] == "client_secret"
    assert "client_secret" in [str(key) for key in result["data_schema"].schema]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret": "9999"}
    )
    await _async_finish_reconfigure(hass, result)

    assert base_config_entry.data["client_secret_source"] == "manual"
    assert base_config_entry.data["client_secret"] == "9999"
    assert "client_secret_env_var" not in base_config_entry.data


async def test_reconfigure_manual_missing_secret(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the manual secret step rejects an empty secret."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    result = await _async_start_reconfigure(hass, base_config_entry, _user_input())
    assert result["step_id"] == "client_secret"
    assert _schema_default(result, "client_secret") == "5678"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret": ""}
    )
    assert result["step_id"] == "client_secret"
    assert result["errors"] == {"client_secret": "missing_client_secret"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"client_secret": "5678"}
    )
    await _async_finish_reconfigure(hass, result)


@pytest.mark.parametrize("base_config_entry", [ENVIRONMENT_ENTRY], indirect=True)
async def test_setup_uses_environment_secret(
    environment_secret,
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test an entry using the environment secret loads."""
    assert base_config_entry.state is ConfigEntryState.LOADED


async def _async_reconfigure(
    hass, requests_mock, entry, user_input=RECONFIGURE_CONFIG_ENTRY, token_file=None
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
