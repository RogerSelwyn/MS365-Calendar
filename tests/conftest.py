# pylint: disable=protected-access,redefined-outer-name, unused-argument, line-too-long, unused-import
"""Global fixtures for integration."""

import os
import pathlib
import sys
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest
from aiohttp import ClientWebSocketResponse
from aiohttp.test_utils import TestClient
from homeassistant.core import Event, HomeAssistant
from pytest_homeassistant_custom_component.typing import (
    ClientSessionGenerator,
    WebSocketGenerator,
)
from requests_mock import Mocker

from custom_components.ms365_calendar.classes import permissions
from custom_components.ms365_calendar.integration import filemgmt_integration
from custom_components.ms365_calendar.integration.const_integration import DOMAIN

from .helpers.const import BASE_CONFIG_ENTRY, TITLE
from .helpers.mock_config_entry import MS365MockConfigEntry

# from .helpers.mocks import (  # noqa: F401
#     all_day_event_mocks,
#     no_events_mocks,
#     not_started_event_mocks,
#     standard_mocks,
#     started_event_mocks,
# )
from .helpers.mocks import MS365MOCKS
from .helpers.utils import build_token_file

pytest_plugins = "pytest_homeassistant_custom_component"  # pylint: disable=invalid-name
THIS_MODULE = sys.modules[__name__]


@pytest.fixture(autouse=True)
def storage_path_setup():
    """Setup the storage paths."""
    tk_path = pathlib.Path(__file__).parent.joinpath("data/storage/tokens")
    yml_path = pathlib.Path(__file__).parent.joinpath(
        "data/storage/ms365_calendars_test.yaml"
    )

    with patch.object(
        permissions,
        "build_config_file_path",
        return_value=tk_path,
    ):
        with patch.object(
            filemgmt_integration,
            "build_config_file_path",
            return_value=yml_path,
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


@pytest.fixture(name="ms365_tidy_storage", autouse=True)
def ms365_tidy_storage_fixture():
    """Tidy up tokens before test."""
    directory = pathlib.Path(__file__).parent.joinpath("data/storage/tokens")
    files_in_directory = os.listdir(directory)
    for file in files_in_directory:
        path_to_file = os.path.join(directory, file)
        os.remove(path_to_file)

    directory = pathlib.Path(__file__).parent.joinpath("data/storage")
    files_in_directory = os.listdir(directory)
    filtered_files = [file for file in files_in_directory if file.endswith(".yaml")]
    for file in filtered_files:
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
    perms = "Calendars.Read"
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
    build_token_file("Calendars.ReadWrite")
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    data = deepcopy(BASE_CONFIG_ENTRY)
    data["enable_update"] = True
    hass.config_entries.async_update_entry(base_config_entry, data=data)
    print(base_config_entry.data)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()


@dataclass
class ListenerSetupData:
    """A collection of data set up by the listener_setup fixture."""

    hass: HomeAssistant
    client: TestClient
    event_listener: Mock
    events: any


@pytest.fixture
async def listener_setup(
    hass: HomeAssistant,
    hass_client_no_auth: ClientSessionGenerator,
) -> ListenerSetupData:
    """Set up integration, client and webhook url."""

    client = await hass_client_no_auth()

    events = []

    async def event_listener(event: Event) -> None:
        events.append(event)

    hass.bus.async_listen(f"{DOMAIN}_create_calendar_event", event_listener)
    hass.bus.async_listen(f"{DOMAIN}_modify_calendar_event", event_listener)
    hass.bus.async_listen(f"{DOMAIN}_remove_calendar_event", event_listener)
    hass.bus.async_listen(f"{DOMAIN}_remove_calendar_recurrences", event_listener)
    hass.bus.async_listen(f"{DOMAIN}_respond_calendar_event", event_listener)

    return ListenerSetupData(hass, client, event_listener, events)


class Client:
    """Test client with helper methods for calendar websocket."""

    def __init__(self, client: ClientWebSocketResponse) -> None:
        """Initialize Client."""
        self.client = client
        self.id = 0

    async def cmd(
        self, cmd: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a command and receive the json result."""
        self.id += 1
        await self.client.send_json(
            {
                "id": self.id,
                "type": f"calendar/event/{cmd}",
                **(payload if payload is not None else {}),
            }
        )
        resp = await self.client.receive_json()
        assert resp.get("id") == self.id
        return resp

    async def cmd_result(
        self, cmd: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Send a command and parse the result."""
        resp = await self.cmd(cmd, payload)
        assert resp.get("success")
        assert resp.get("type") == "result"
        return resp.get("result")


type ClientFixture = Callable[[], Awaitable[Client]]


@pytest.fixture
async def ws_client(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
) -> ClientFixture:
    """Fixture for creating the test websocket client."""

    async def create_client() -> Client:
        ws_client = await hass_ws_client(hass)
        return Client(ws_client)

    return create_client
