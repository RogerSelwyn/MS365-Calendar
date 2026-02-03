# pylint: disable=line-too-long, unused-argument
"""Test tenant_id functionality."""

import json
from copy import deepcopy
from enum import Enum

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from requests_mock import Mocker

from .const import CLIENT_ID
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import (
    build_retrieved_token,
    build_token_url,
    load_json,
    mock_call,
    mock_cn21v_token,
)
from .integration import get_tenant_id
from .integration.const_integration import (
    AUTH_CALLBACK_PATH_DEFAULT,
    BASE_CONFIG_ENTRY,
    BASE_TOKEN_PERMS,
    COUNTRY_CONFIG_ENTRY,
    DOMAIN,
    URL,
)
from .integration.helpers_integration.mocks import MS365MOCKS


# --- Unit tests for get_tenant_id ---


class TestGetTenantId:
    """Tests for the get_tenant_id helper function."""

    def test_returns_common_when_no_api_options(self):
        """Test that 'common' is returned when api_options is missing."""
        entry_data = {"entity_name": "test"}
        assert get_tenant_id(entry_data) == "common"

    def test_returns_common_when_api_options_empty(self):
        """Test that 'common' is returned when api_options has no tenant_id."""
        entry_data = {"api_options": {"country": "Default"}}
        assert get_tenant_id(entry_data) == "common"

    def test_returns_common_when_tenant_id_blank(self):
        """Test that 'common' is returned when tenant_id is empty string."""
        entry_data = {"api_options": {"country": "Default", "tenant_id": ""}}
        assert get_tenant_id(entry_data) == "common"

    def test_returns_common_when_tenant_id_whitespace(self):
        """Test that 'common' is returned when tenant_id is only whitespace."""
        entry_data = {"api_options": {"country": "Default", "tenant_id": "   "}}
        assert get_tenant_id(entry_data) == "common"

    def test_returns_tenant_id_when_set(self):
        """Test that tenant_id is returned when set."""
        entry_data = {
            "api_options": {
                "country": "Default",
                "tenant_id": "my-tenant-uuid",
            }
        }
        assert get_tenant_id(entry_data) == "my-tenant-uuid"

    def test_strips_whitespace_from_tenant_id(self):
        """Test that leading/trailing whitespace is stripped from tenant_id."""
        entry_data = {
            "api_options": {
                "country": "Default",
                "tenant_id": "  my-tenant-uuid  ",
            }
        }
        assert get_tenant_id(entry_data) == "my-tenant-uuid"


# --- Integration tests for config flow with tenant_id ---

TENANT_ID = "11111111-2222-3333-4444-555555555555"
TENANT_TOKEN_URL_ASSERT = (
    f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/"
    + "authorize?client_id="
)


def _config_entry_with_tenant(tenant_id):
    """Build a config entry dict with a specific tenant_id."""
    entry = deepcopy(BASE_CONFIG_ENTRY)
    entry["api_options"]["tenant_id"] = tenant_id
    return entry


class TenantURL(Enum):
    """Tenant-specific URLs for mocking."""

    OPENID = f"https://login.microsoftonline.com/{TENANT_ID}/v2.0/.well-known/openid-configuration"


def _mock_tenant_token(requests_mock, scope):
    """Mock token response for tenant-specific endpoint."""
    token = json.dumps(build_retrieved_token(scope))
    requests_mock.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        text=token,
    )
    # Mock tenant-specific openid discovery
    openid_data = load_json("O365/openid.json")
    openid_data = openid_data.replace("/common/", f"/{TENANT_ID}/")
    requests_mock.get(TenantURL.OPENID.value, text=openid_data)


async def test_flow_with_tenant_id(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test config flow passes tenant_id through to the auth URL."""
    _mock_tenant_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=_config_entry_with_tenant(TENANT_ID),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    auth_url = result["description_placeholders"]["auth_url"]
    # The O365 library should construct the URL with our tenant_id
    assert auth_url.startswith(TENANT_TOKEN_URL_ASSERT), (
        f"Expected auth URL to start with tenant-specific prefix, got: {auth_url}"
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "result" in result
    assert result["result"].data["api_options"]["tenant_id"] == TENANT_ID


async def test_flow_without_tenant_id_uses_common(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test config flow uses /common when tenant_id is not set."""
    from .const import TOKEN_URL_ASSERT

    mock_call(requests_mock, URL.OPENID, "openid")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=BASE_CONFIG_ENTRY,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    auth_url = result["description_placeholders"]["auth_url"]
    assert auth_url.startswith(f"{TOKEN_URL_ASSERT}{CLIENT_ID}"), (
        f"Expected auth URL to use /common/, got: {auth_url}"
    )


async def test_reconfigure_preserves_tenant_id(
    hass: HomeAssistant,
    requests_mock: Mocker,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test reconfigure flow preserves existing tenant_id."""
    _mock_tenant_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": base_config_entry.entry_id,
        },
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    # Reconfigure with a tenant_id
    reconfigure_input = deepcopy(BASE_CONFIG_ENTRY)
    del reconfigure_input["entity_name"]
    reconfigure_input["api_options"]["tenant_id"] = TENANT_ID

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=reconfigure_input,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    auth_url = result["description_placeholders"]["auth_url"]
    assert f"/{TENANT_ID}/" in auth_url

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(result, AUTH_CALLBACK_PATH_DEFAULT),
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


# --- CN21V (China cloud) integration tests ---

async def test_flow_cn21v_with_tenant_id(
    hass: HomeAssistant,
    requests_mock: Mocker,
) -> None:
    """Test config flow with CN21V country uses tenant-specific authority URL."""
    MS365MOCKS.cn21v_mocks(requests_mock)
    mock_cn21v_token(requests_mock, BASE_TOKEN_PERMS)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result.get("type") is FlowResultType.FORM
    assert result["step_id"] == "user"

    cn21v_entry = deepcopy(COUNTRY_CONFIG_ENTRY)
    cn21v_entry["api_options"]["tenant_id"] = TENANT_ID

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=cn21v_entry,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "request_default"
    auth_url = result["description_placeholders"]["auth_url"]
    # Verify the CN21V domain is used (not the default login.microsoftonline.com)
    assert "login.partner.microsoftonline.cn" in auth_url, (
        f"Expected CN21V auth URL, got: {auth_url}"
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "url": build_token_url(
                result,
                "https://login.partner.microsoftonline.cn/common/oauth2/nativeclient",
            ),
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "result" in result
    assert result["result"].data["api_options"]["tenant_id"] == TENANT_ID
