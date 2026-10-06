# pylint: disable=unused-argument,line-too-long
"""Test the values accepted by the service schemas."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from requests_mock import Mocker
from voluptuous.error import MultipleInvalid
import yaml

from ..helpers.utils import mock_call
from .const_integration import DOMAIN, URL

CALENDAR_NAME = "calendar.test_calendar1"
EVENT_NAME = "event1"
CREATE_DATA = {
    "entity_id": CALENDAR_NAME,
    "subject": "Department Party",
    "start": "2022-03-22T20:00:00.000Z",
    "end": "2022-03-22T22:00:00.000Z",
}
MODIFY_DATA = {"entity_id": CALENDAR_NAME, "event_id": EVENT_NAME}
SERVICES_YAML = (
    Path(__file__).parents[2] / "custom_components" / DOMAIN / "services.yaml"
)
GRAPH_KEYS = {"sensitivity": "sensitivity", "show_as": "showAs"}


def _service_options(service, field):
    """Get the values services.yaml offers for a field."""
    services = yaml.safe_load(SERVICES_YAML.read_text(encoding="utf8"))
    options = services[service]["fields"][field]["selector"]["select"]["options"]
    return [option["value"] for option in options]


def _saved_payload(mock_save):
    """Get the payload Event.save sends to MS Graph."""
    event = mock_save.call_args.args[0]
    if event.object_id:
        return event.to_api_data(restrict_keys=event._track_changes)  # noqa: SLF001
    return event.to_api_data()


async def _async_call_service(hass, service, data):
    """Call the service and return the payload sent to MS Graph."""
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await hass.services.async_call(
            DOMAIN,
            service,
            data,
            blocking=True,
            return_response=False,
        )
    return _saved_payload(mock_save)


@pytest.mark.parametrize(
    ("service", "data"),
    [
        ("create_calendar_event", CREATE_DATA),
        ("modify_calendar_event", MODIFY_DATA),
    ],
)
async def test_services_yaml_options(
    hass: HomeAssistant,
    setup_update_integration,
    requests_mock: Mocker,
    service,
    data,
) -> None:
    """Test every sensitivity and show_as option in services.yaml reaches MS Graph."""
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{EVENT_NAME}",
    )

    for field, graph_key in GRAPH_KEYS.items():
        for value in _service_options(service, field):
            payload = await _async_call_service(hass, service, {**data, field: value})
            assert payload[graph_key] == value


async def test_create_event_with_names(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test the capitalised names used in the docs and field descriptions are accepted."""
    names = {
        "sensitivity": {
            "Normal": "normal",
            "Personal": "personal",
            "Private": "private",
            "Confidential": "confidential",
        },
        "show_as": {
            "Free": "free",
            "Tentative": "tentative",
            "Busy": "busy",
            "Oof": "oof",
            "WorkingElsewhere": "workingElsewhere",
            "Unknown": "unknown",
        },
    }

    for field, values in names.items():
        for name, graph_value in values.items():
            payload = await _async_call_service(
                hass, "create_calendar_event", {**CREATE_DATA, field: name}
            )
            assert payload[GRAPH_KEYS[field]] == graph_value

    with pytest.raises(MultipleInvalid):
        await _async_call_service(
            hass, "create_calendar_event", {**CREATE_DATA, "show_as": "Away"}
        )


async def test_modify_event_with_get_calendar_events_values(
    hass: HomeAssistant,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test sensitivity and show_as from get_calendar_events can be passed to modify."""
    result = await hass.services.async_call(
        DOMAIN,
        "get_calendar_events",
        {
            "entity_id": CALENDAR_NAME,
            "start_date_time": (dt_util.utcnow() + timedelta(hours=-24)).isoformat(),
            "end_date_time": (dt_util.utcnow() + timedelta(hours=24)).isoformat(),
        },
        blocking=True,
        return_response=True,
    )
    event = next(
        event
        for event in result[CALENDAR_NAME]["events"]
        if event["sensitivity"] == "Private"
    )
    assert event["show_as"] == "Busy"

    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{EVENT_NAME}",
    )
    payload = await _async_call_service(
        hass,
        "modify_calendar_event",
        {
            **MODIFY_DATA,
            "sensitivity": event["sensitivity"],
            "show_as": event["show_as"],
        },
    )

    assert payload["sensitivity"] == "private"
    assert payload["showAs"] == "busy"
