# pylint: disable=protected-access,redefined-outer-name, unused-argument, line-too-long, unused-import
"""Global fixtures for integration."""

import sys
from copy import deepcopy
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from requests_mock import Mocker

from .const import TITLE, TOKEN_LOCATION
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import build_token_file
from .integration import permissions
from .integration.const_integration import (
    BASE_CONFIG_ENTRY,
    BASE_TOKEN_PERMS,
    DOMAIN,
    UPDATE_OPTIONS,
    UPDATE_TOKEN_PERMS,
)
from .integration.helpers_integration.mocks import MS365MOCKS

pytest_plugins = [
    "pytest_homeassistant_custom_component",
    "tests.integration.fixtures",
]  # pylint: disable=invalid-name
THIS_MODULE = sys.modules[__name__]


@pytest.fixture(autouse=True)
def folder_setup(tmp_path):
    """Setup the testing session."""
    directory = tmp_path / TOKEN_LOCATION
    directory.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def token_storage_path_setup(tmp_path):
    """Setup the storage paths."""
    tk_path = tmp_path / TOKEN_LOCATION

    with patch.object(
        permissions,
        "build_config_file_path",
        return_value=tk_path,
    ):
        yield


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # pylint: disable=unused-argument
    """Automatically enable loading custom integrations in all tests."""
    return


@pytest.fixture(autouse=True)
async def request_setup(current_request_with_host: None) -> None:  # pylint: disable=unused-argument
    """Request setup."""


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture
def base_config_entry(request, hass: HomeAssistant) -> MS365MockConfigEntry:
    """Create MS365 entry in Home Assistant."""
    data = deepcopy(BASE_CONFIG_ENTRY)
    options = None
    if hasattr(request, "param"):
        for key, value in request.param.items():
            if key == "options":
                options = value
            else:
                data[key] = value
    entry = MS365MockConfigEntry(
        domain=DOMAIN, title=TITLE, unique_id=DOMAIN, data=data, options=options
    )
    entry.runtime_data = None
    return entry


@pytest.fixture
def base_token(request, tmp_path):
    """Setup a basic token."""
    perms = BASE_TOKEN_PERMS
    if hasattr(request, "param"):
        perms = request.param
    build_token_file(tmp_path, perms)


@pytest.fixture
async def setup_base_integration(
    request,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Fixture for setting up the component."""
    method_name = "standard_mocks"
    if hasattr(request, "param") and "method_name" in request.param:
        method_name = request.param["method_name"]

    mock_method = getattr(MS365MOCKS, method_name)
    mock_method(requests_mock)

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
async def setup_update_integration(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Fixture for setting up the component."""
    build_token_file(tmp_path, UPDATE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    data = deepcopy(BASE_CONFIG_ENTRY)
    for key, value in UPDATE_OPTIONS.items():
        data[key] = value
    hass.config_entries.async_update_entry(base_config_entry, data=data)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()
