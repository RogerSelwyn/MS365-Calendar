# pylint: disable=redefined-outer-name, unused-argument
"""Fixtures specific to the integration."""

from collections.abc import Awaitable, Callable
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

from custom_components.ms365_calendar.integration import filemgmt_integration

from ..const import STORAGE_LOCATION
from .const_integration import DOMAIN


@pytest.fixture(autouse=True)
def yaml_storage_path_setup(tmp_path):
    """Setup the storage paths."""
    yml_path = tmp_path / STORAGE_LOCATION / f"{DOMAIN}s_test.yaml"

    with patch.object(
        filemgmt_integration,
        "build_config_file_path",
        return_value=yml_path,
    ):
        yield


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
