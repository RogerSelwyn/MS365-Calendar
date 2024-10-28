# pylint: disable=protected-access,redefined-outer-name, unused-argument, line-too-long, unused-import
"""Global fixtures for integration."""

import os
import shutil
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from requests_mock import Mocker

from .const import STORAGE_LOCATION, TITLE, TOKEN_LOCATION
from .helpers.mock_config_entry import MS365MockConfigEntry
from .helpers.utils import build_token_file
from .integration import permissions
from .integration.const import (
    BASE_CONFIG_ENTRY,
    BASE_TOKEN_PERMS,
    DOMAIN,
    UPDATE_TOKEN_PERMS,
)
from .integration.helpers.mocks import MS365MOCKS

pytest_plugins = [
    "pytest_homeassistant_custom_component",
    "tests.integration.fixtures",
]  # pylint: disable=invalid-name
THIS_MODULE = sys.modules[__name__]


@pytest.fixture(autouse=True, scope="session")
def session_setup():
    """Setup the testing session."""
    Path(TOKEN_LOCATION).mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(STORAGE_LOCATION)


@pytest.fixture(autouse=True)
def token_storage_path_setup():
    """Setup the storage paths."""
    tk_path = TOKEN_LOCATION

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


@pytest.fixture(name="ms365_tidy_token_storage", autouse=True)
def ms365_tidy_token_storage_fixture():
    """Tidy up tokens before test."""
    directory = TOKEN_LOCATION
    files_in_directory = os.listdir(directory)
    for file in files_in_directory:
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)


@pytest.fixture
def base_config_entry(request, hass: HomeAssistant) -> MS365MockConfigEntry:
    """Create MS365 entry in Home Assistant."""
    data = deepcopy(BASE_CONFIG_ENTRY)
    if hasattr(request, "param"):
        for key, value in request.param.items():
            data[key] = value
    entry = MS365MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        unique_id=DOMAIN,
        data=data,
    )
    entry.runtime_data = None
    return entry


@pytest.fixture
def update_config_entry(hass: HomeAssistant) -> MS365MockConfigEntry:
    """Create MS365 entry in Home Assistant."""
    data = deepcopy(BASE_CONFIG_ENTRY)
    data["enable_update"] = True
    entry = MS365MockConfigEntry(
        domain=DOMAIN,
        title=TITLE,
        unique_id=DOMAIN,
        data=data,
    )
    entry.runtime_data = None
    return entry


@pytest.fixture
def base_token(request):
    """Setup a basic token."""
    perms = BASE_TOKEN_PERMS
    if hasattr(request, "param"):
        perms = request.param
    build_token_file(perms)


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
    if hasattr(request, "param"):
        if "method_name" in request.param:
            method_name = request.param["method_name"]

    mock_method = getattr(MS365MOCKS, method_name)
    mock_method(requests_mock)

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
async def setup_update_integration(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Fixture for setting up the component."""
    build_token_file(UPDATE_TOKEN_PERMS)
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    data = deepcopy(BASE_CONFIG_ENTRY)
    data["enable_update"] = True
    hass.config_entries.async_update_entry(base_config_entry, data=data)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()
