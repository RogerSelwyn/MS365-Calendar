"""Test migration"""

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from requests_mock import Mocker

from .helpers.utils import mock_token
from .integration.const_integration import (
    BASE_TOKEN_PERMS,
    DOMAIN,
    MIGRATION_CONFIG_ENTRY,
)
from .integration.helpers_integration.mocks import MS365MOCKS


async def test_default_flow(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the default config_flow."""
    mock_token(requests_mock, BASE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)

    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MIGRATION_CONFIG_ENTRY,
    )
    assert (
        f"Could not locate token at {tmp_path}/storage/tokens/{DOMAIN}_test.token"
        in caplog.text
    )
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=MIGRATION_CONFIG_ENTRY,
    )
