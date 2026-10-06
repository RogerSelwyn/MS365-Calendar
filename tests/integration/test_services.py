# pylint: disable=unused-argument,line-too-long,wrong-import-order
"""Test service usage."""

from datetime import datetime, timedelta
import logging
from unittest.mock import patch

import pytest
from homeassistant.components.calendar import CREATE_EVENT_SERVICE, SERVICE_GET_EVENTS
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from requests_mock import Mocker
from voluptuous.error import MultipleInvalid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from custom_components.ms365_calendar.const import CONF_ENABLE_UPDATE

from ..conftest import MS365MockConfigEntry
from ..helpers.utils import mock_call
from .const_integration import DOMAIN, URL
from .fixtures import ClientFixture, ListenerSetupData

START_BASE = datetime(2020, 1, 1, 0, 0, 0, tzinfo=ZoneInfo(key="UTC"))
END_BASE = datetime(2020, 1, 1, 23, 59, 59, tzinfo=ZoneInfo(key="UTC"))


async def test_update_service_setup(
    hass: HomeAssistant,
    setup_update_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the reconfigure flow."""
    assert base_config_entry.data[CONF_ENABLE_UPDATE]
    assert hass.services.has_service(DOMAIN, "create_calendar_event")
    assert hass.services.has_service(DOMAIN, "modify_calendar_event")
    assert hass.services.has_service(DOMAIN, "remove_calendar_event")
    assert hass.services.has_service(DOMAIN, "respond_calendar_event")


async def test_get_events_inside_range(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get events inside range - HA Service."""
    calendar_name = "calendar.test_calendar1"
    start_date = dt_util.utcnow() + timedelta(hours=-24)
    end_date = dt_util.utcnow() + timedelta(hours=24)
    result = await hass.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": calendar_name,
            "start_date_time": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date_time": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        blocking=True,
        return_response=True,
    )
    assert calendar_name in result
    assert "events" in result[calendar_name]
    assert len(result[calendar_name]["events"]) == 2


async def test_get_events_outside_range(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get events outside range - HA Service."""
    calendar_name = "calendar.test_calendar1"
    result = await hass.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": calendar_name,
            "start_date_time": "2022-03-22T20:00:00.000Z",
            "end_date_time": "2022-03-22T22:00:00.000Z",
        },
        blocking=True,
        return_response=True,
    )
    assert calendar_name in result
    assert "events" in result[calendar_name]
    assert len(result[calendar_name]["events"]) == 2


async def test_get_calendar_events_service_setup(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get_calendar_events is available without calendar updates enabled."""
    assert hass.services.has_service(DOMAIN, "get_calendar_events")


async def test_get_calendar_events_inside_range(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get_calendar_events inside range returns attendees and organizer."""
    calendar_name = "calendar.test_calendar1"
    start_date = dt_util.utcnow() + timedelta(hours=-24)
    end_date = dt_util.utcnow() + timedelta(hours=24)
    result = await hass.services.async_call(
        DOMAIN,
        "get_calendar_events",
        {
            "entity_id": calendar_name,
            "start_date_time": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_date_time": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        blocking=True,
        return_response=True,
    )
    events = result[calendar_name]["events"]
    assert len(events) == 2
    with_attendees = [event for event in events if event["attendees"]]
    assert len(with_attendees) == 1
    event = with_attendees[0]
    assert event["attendees"] == [
        {"email": "jane@nomail.com", "type": "required", "status": "not_responded"}
    ]
    assert event["organizer"] == "john@nomail.com"
    assert isinstance(event["start"], str)
    assert isinstance(event["end"], str)
    assert event["uid"]


async def test_get_calendar_events_outside_range(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get_calendar_events outside the synced range fetches from MS Graph."""
    calendar_name = "calendar.test_calendar1"
    result = await hass.services.async_call(
        DOMAIN,
        "get_calendar_events",
        {
            "entity_id": calendar_name,
            "start_date_time": "2022-03-22T20:00:00.000Z",
            "end_date_time": "2022-03-22T22:00:00.000Z",
        },
        blocking=True,
        return_response=True,
    )
    events = result[calendar_name]["events"]
    assert len(events) == 2
    assert all("attendees" in event and "organizer" in event for event in events)


async def test_get_calendar_events_naive_datetimes(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get_calendar_events treats naive datetimes as local time."""
    calendar_name = "calendar.test_calendar1"
    result = await hass.services.async_call(
        DOMAIN,
        "get_calendar_events",
        {
            "entity_id": calendar_name,
            "start_date_time": "2022-03-22T20:00:00",
            "end_date_time": "2022-03-22T22:00:00",
        },
        blocking=True,
        return_response=True,
    )
    events = result[calendar_name]["events"]
    assert len(events) == 2


async def test_get_calendar_events_end_before_start(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get_calendar_events rejects an end before the start."""
    start_date = dt_util.utcnow()
    end_date = start_date + timedelta(hours=-1)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "get_calendar_events",
            {
                "entity_id": "calendar.test_calendar1",
                "start_date_time": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_date_time": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
            blocking=True,
            return_response=True,
        )

async def test_get_events_too_quick(
    hass: HomeAssistant,
    setup_base_integration,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test error fetching data."""
    coordinator = base_config_entry.runtime_data.coordinator[0]
    coordinator.data = None
    calendar_name = "calendar.test_calendar1"
    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            CALENDAR_DOMAIN,
            SERVICE_GET_EVENTS,
            {
                "entity_id": calendar_name,
                "start_date_time": "2022-03-22T20:00:00.000Z",
                "end_date_time": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=True,
        )
    assert (
        str(exc_info.value)
        == "Unable to get events: Sync from server has not completed"
    )


@pytest.mark.parametrize(
    "setup_base_integration", [{"method_name": "no_events_mocks"}], indirect=True
)
async def test_get_events_no_events(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get events - None returned."""
    calendar_name = "calendar.test_calendar1"
    result = await hass.services.async_call(
        CALENDAR_DOMAIN,
        SERVICE_GET_EVENTS,
        {
            "entity_id": calendar_name,
            "start_date_time": "2022-03-22T20:00:00.000Z",
            "end_date_time": "2022-03-22T22:00:00.000Z",
        },
        blocking=True,
        return_response=True,
    )
    assert calendar_name in result
    assert "events" in result[calendar_name]
    assert len(result[calendar_name]["events"]) == 0


async def test_get_events_ha_error(
    hass: HomeAssistant,
    setup_base_integration,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test get events - HA error returned."""
    calendar_name = "calendar.test_calendar1"

    with patch(
        f"custom_components.{DOMAIN}.integration.calendar_integration.CalendarEvent",
        side_effect=HomeAssistantError(),
    ):
        await hass.services.async_call(
            CALENDAR_DOMAIN,
            SERVICE_GET_EVENTS,
            {
                "entity_id": calendar_name,
                "start_date_time": "2022-03-22T20:00:00.000Z",
                "end_date_time": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=True,
        )
    assert "Invalid event found - Error" in caplog.text


async def test_create_event(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
) -> None:
    """Test create event - HA service."""
    calendar_name = "calendar.test_calendar1"
    with patch("O365.calendar.Event.save") as mock_save:
        await hass.services.async_call(
            CALENDAR_DOMAIN,
            CREATE_EVENT_SERVICE,
            {
                "entity_id": calendar_name,
                "summary": "Department Party",
                "description": "Meeting to provide technical review for 'Phoenix' design.",
                "start_date_time": "2022-03-22T20:00:00.000Z",
                "end_date_time": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()
    assert mock_save.called
    assert len(listener_setup.events) == 1
    assert listener_setup.events[0].event_type == f"{DOMAIN}_create_calendar_event"


async def test_create_ms365_event(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
    requests_mock: Mocker,
) -> None:
    """Test create event - MS365 service."""

    event_name = "event1"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{event_name}",
    )

    calendar_name = "calendar.test_calendar1"
    with patch("O365.calendar.Event.save") as mock_save:
        response = await hass.services.async_call(
            DOMAIN,
            "create_calendar_event",
            {
                "entity_id": calendar_name,
                "subject": "Department Party",
                "body": "Meeting to provide technical review for 'Phoenix' design.",
                "start": "2022-03-22T20:00:00.000Z",
                "end": "2022-03-23T22:00:00.000Z",
                "attendees": [{"email": "example@example.com", "type": "Required"}],
                "is_all_day": True,
            },
            blocking=True,
            return_response=True,
        )
    await hass.async_block_till_done()
    assert response == {calendar_name: {"uid": None}}
    assert mock_save.called
    assert len(listener_setup.events) == 1
    assert listener_setup.events[0].event_type == f"{DOMAIN}_create_calendar_event"


async def test_create_inconsistent_timezones(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
    requests_mock: Mocker,
) -> None:
    """Test create event with inconsistent timezones - MS365 service."""

    event_name = "event1"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{event_name}",
    )

    calendar_name = "calendar.test_calendar1"
    with pytest.raises(MultipleInvalid) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "create_calendar_event",
            {
                "entity_id": calendar_name,
                "subject": "Department Party",
                "body": "Meeting to provide technical review for 'Phoenix' design.",
                "start": "2022-03-22T20:00:00.000+0200",
                "end": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )
    assert str(exc_info.value) == "Expected all values to have the same timezone"


async def test_inconsistent_timezones(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
) -> None:
    """Test create event with inconsistent timezones - HA service."""
    calendar_name = "calendar.test_calendar1"
    with pytest.raises(MultipleInvalid) as exc_info:
        await hass.services.async_call(
            CALENDAR_DOMAIN,
            CREATE_EVENT_SERVICE,
            {
                "entity_id": calendar_name,
                "summary": "Department Party",
                "description": "Meeting to provide technical review for 'Phoenix' design.",
                "start_date_time": "2022-03-22T20:00:00.000+0200",
                "end_date_time": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()

    assert str(exc_info.value) == "Expected all values to have the same timezone"


async def test_create_event_no_perms(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test create event - no perms."""
    calendar_name = "calendar.test_calendar1"
    failed_perm = "calendar.failed_perm"
    with (
        patch(
            f"custom_components.{DOMAIN}.integration.calendar_integration.PERM_CALENDARS_READWRITE",
            failed_perm,
        ),
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            CALENDAR_DOMAIN,
            CREATE_EVENT_SERVICE,
            {
                "entity_id": calendar_name,
                "summary": "Department Party",
                "description": "Meeting to provide technical review for 'Phoenix' design.",
                "start_date_time": "2022-03-22T20:00:00.000Z",
                "end_date_time": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )

    assert str(exc_info.value) == f"Not authorised requires permission: {failed_perm}"


async def test_update_event(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
    requests_mock: Mocker,
) -> None:
    """Test update event - MS365 service."""

    event_name = "event1"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{event_name}",
    )

    calendar_name = "calendar.test_calendar1"
    with patch("O365.calendar.Event.save") as mock_save:
        await hass.services.async_call(
            DOMAIN,
            "modify_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "subject": "Department Party",
                "body": "Meeting to provide technical review for 'Phoenix' design.",
                "start": "2022-03-22T20:00:00.000Z",
                "end": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()
    assert mock_save.called
    assert len(listener_setup.events) == 1
    assert listener_setup.events[0].event_type == f"{DOMAIN}_modify_calendar_event"


async def test_update_event_no_perms(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test update event - no perms."""
    event_name = "event1"
    calendar_name = "calendar.test_calendar1"
    failed_perm = "calendar.failed_perm"
    with (
        patch(
            f"custom_components.{DOMAIN}.integration.calendar_integration.PERM_CALENDARS_READWRITE",
            failed_perm,
        ),
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "modify_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "subject": "Department Party",
                "body": "Meeting to provide technical review for 'Phoenix' design.",
                "start": "2022-03-22T20:00:00.000Z",
                "end": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )

    assert str(exc_info.value) == f"Not authorised requires permission: {failed_perm}"


async def test_update_group_calendar(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test update group calendar event - not allowed."""
    event_name = "event1"
    calendar_name = "calendar.test_calendar2"
    with (
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "modify_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "subject": "Department Party",
                "body": "Meeting to provide technical review for 'Phoenix' design.",
                "start": "2022-03-22T20:00:00.000Z",
                "end": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )

    assert (
        str(exc_info.value)
        == f"O365 Python does not have capability to update/respond to group calendar events: {calendar_name}"
    )


async def test_update_recurring_event(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update recurring event - HA API call."""

    calendar_name = "calendar.test_calendar1"
    event_name = "event2"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event2",
        f"calendar1/events/{event_name}",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2022-10-24T07:00:00.0000000",
                    "dtend": "2022-10-24T07:30:00.0000000",
                    "rrule": "COUNT=5;FREQ=DAILY",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    recurrence = _saved_recurrence(mock_save)
    assert recurrence["pattern"] == {"type": "daily", "interval": 1}
    assert recurrence["range"]["type"] == "numbered"
    assert recurrence["range"]["numberOfOccurrences"] == 5

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2022-10-24T07:00:00.0000000",
                    "dtend": "2022-10-24T07:30:00.0000000",
                    "rrule": "UNTIL=20990101T010101;FREQ=WEEKLY;BYDAY=MO",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    recurrence = _saved_recurrence(mock_save)
    assert recurrence["pattern"]["type"] == "weekly"
    assert recurrence["pattern"]["daysOfWeek"] == ["monday"]
    assert recurrence["range"]["endDate"] == "2099-01-01"

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2022-10-24T07:00:00.0000000",
                    "dtend": "2022-10-24T07:30:00.0000000",
                    "rrule": "UNTIL=20990101T010101;FREQ=MONTHLY",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    recurrence = _saved_recurrence(mock_save)
    assert recurrence["pattern"]["type"] == "absoluteMonthly"
    assert recurrence["pattern"]["dayOfMonth"] == 24

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2022-10-24T07:00:00.0000000",
                    "dtend": "2022-10-24T07:30:00.0000000",
                    "rrule": "FREQ=MONTHLY;BYDAY=+4FR",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    recurrence = _saved_recurrence(mock_save)
    assert recurrence["pattern"]["type"] == "relativeMonthly"
    assert recurrence["pattern"]["daysOfWeek"] == ["friday"]
    assert recurrence["pattern"]["index"] == "fourth"

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2022-10-24T07:00:00.0000000",
                    "dtend": "2022-10-24T07:30:00.0000000",
                    "rrule": "UNTIL=20990101T010101;FREQ=YEARLY",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    recurrence = _saved_recurrence(mock_save)
    assert recurrence["pattern"]["type"] == "absoluteYearly"
    assert recurrence["pattern"]["month"] == 10
    assert recurrence["pattern"]["dayOfMonth"] == 24


async def test_update_event_keeps_omitted_fields(
    hass: HomeAssistant,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update event - fields not supplied are left unchanged."""

    event_name = "event3"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event_categories",
        f"calendar1/events/{event_name}",
    )

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await hass.services.async_call(
            DOMAIN,
            "modify_calendar_event",
            {
                "entity_id": "calendar.test_calendar1",
                "event_id": event_name,
                "subject": "Bank holiday",
            },
            blocking=True,
            return_response=False,
        )

    payload = _saved_payload(mock_save)
    assert payload == {"subject": "Bank holiday"}


async def test_update_all_day_event_to_timed(
    hass: HomeAssistant,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update event - times of day on an all day event make it timed."""

    event_name = "event3"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event_categories",
        f"calendar1/events/{event_name}",
    )

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await hass.services.async_call(
            DOMAIN,
            "modify_calendar_event",
            {
                "entity_id": "calendar.test_calendar1",
                "event_id": event_name,
                "start": "2026-03-22T09:00:00-07:00",
                "end": "2026-03-22T10:00:00-07:00",
            },
            blocking=True,
            return_response=False,
        )

    payload = _saved_payload(mock_save)
    assert payload["isAllDay"] is False
    assert payload["start"]["dateTime"] == "2026-03-22T09:00:00"
    assert payload["end"]["dateTime"] == "2026-03-22T10:00:00"
    assert "categories" not in payload


async def test_update_event_ui_keeps_html_body(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update event - HA API call keeps the HTML body unless the text changed."""

    calendar_name = "calendar.test_calendar1"
    event_name = "event3"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event_categories",
        f"calendar1/events/{event_name}",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Holiday",
                    "dtstart": "2026-03-22",
                    "dtend": "2026-03-24",
                    "description": "Join the meeting now",
                },
            },
        )

    payload = _saved_payload(mock_save)
    assert "body" not in payload
    assert "categories" not in payload

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Holiday",
                    "dtstart": "2026-03-22",
                    "dtend": "2026-03-24",
                    "description": "Back on Tuesday\nCall if urgent",
                },
            },
        )

    payload = _saved_payload(mock_save)
    assert payload["body"] == {
        "contentType": "text",
        "content": "Back on Tuesday\nCall if urgent",
    }


async def test_create_recurring_event_starts_on_event_date(
    ws_client: ClientFixture,
    setup_update_integration,
) -> None:
    """Test create recurring event - HA API call anchors the series on the event."""

    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "create",
            {
                "entity_id": "calendar.test_calendar1",
                "event": {
                    "summary": "Gym",
                    "dtstart": "2099-01-16T18:00:00",
                    "dtend": "2099-01-16T19:00:00",
                    "rrule": "FREQ=WEEKLY;BYDAY=FR;UNTIL=20990320T050000Z",
                    "description": "Line one\nLine two",
                },
            },
        )

    event = mock_save.call_args.args[0]
    recurrence_range = event.recurrence.to_api_data()["range"]
    assert recurrence_range["startDate"] == "2099-01-16"
    # 05:00 UTC on 20 March is still 19 March in the US/Pacific test time zone
    assert recurrence_range["endDate"] == "2099-03-19"
    assert event.to_api_data()["body"] == {
        "contentType": "text",
        "content": "Line one\nLine two",
    }


async def test_update_series_keeps_series_date(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update this and following - HA API call keeps the series dates."""

    calendar_name = "calendar.test_calendar1"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_series_occurrence",
        "calendar1/events/occurrence3",
    )
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_series_master",
        "calendar1/events/master3",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": "occurrence3",
                "recurrence_id": "master3",
                "recurrence_range": "THISANDFUTURE",
                "event": {
                    "summary": "Weekly sync (later)",
                    "dtstart": "2026-11-02T10:30:00-08:00",
                    "dtend": "2026-11-02T11:30:00-08:00",
                    "description": "Weekly sync - agenda: budget",
                    "rrule": "FREQ=WEEKLY;BYDAY=MO",
                },
            },
        )

    # The occurrence is after the change to winter time, the series starts before it
    event = mock_save.call_args.args[0]
    assert event.object_id == "master3"
    payload = _saved_payload(mock_save)
    assert payload["subject"] == "Weekly sync (later)"
    assert payload["start"] == {
        "dateTime": "2026-09-07T10:30:00",
        "timeZone": "Pacific Standard Time",
    }
    assert payload["end"] == {
        "dateTime": "2026-09-07T11:30:00",
        "timeZone": "Pacific Standard Time",
    }
    assert payload["recurrence"]["range"]["startDate"] == "2026-09-07"
    assert "body" not in payload

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        resp = await client.cmd(
            "update",
            {
                "entity_id": calendar_name,
                "uid": "occurrence3",
                "recurrence_id": "master3",
                "recurrence_range": "THISANDFUTURE",
                "event": {
                    "summary": "Weekly sync",
                    "dtstart": "2026-11-03T10:00:00-08:00",
                    "dtend": "2026-11-03T11:00:00-08:00",
                },
            },
        )

    assert not resp["success"]
    assert "date cannot be changed" in resp["error"]["message"]
    assert not mock_save.called


async def test_update_series_from_moved_occurrence(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update this and following - a moved occurrence does not move the series."""

    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_series_exception",
        "calendar1/events/occurrence4",
    )
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_series_master",
        "calendar1/events/master3",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": "calendar.test_calendar1",
                "uid": "occurrence4",
                "recurrence_id": "master3",
                "recurrence_range": "THISANDFUTURE",
                "event": {
                    "summary": "Weekly sync (renamed)",
                    "dtstart": "2026-11-02T08:00:00-08:00",
                    "dtend": "2026-11-02T09:00:00-08:00",
                },
            },
        )

    payload = _saved_payload(mock_save)
    assert payload["subject"] == "Weekly sync (renamed)"
    assert payload["start"]["dateTime"] == "2026-09-07T10:00:00"
    assert payload["end"]["dateTime"] == "2026-09-07T11:00:00"


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Room B", None),
        ("Room C", {"displayName": "Room C"}),
        ("", {"displayName": ""}),
    ],
)
async def test_update_series_ui_location(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
    location,
    expected,
) -> None:
    """Test update this and following - the occurrence's location is not sent."""

    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_series_exception",
        "calendar1/events/occurrence4",
    )
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_series_master",
        "calendar1/events/master3",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": "calendar.test_calendar1",
                "uid": "occurrence4",
                "recurrence_id": "master3",
                "recurrence_range": "THISANDFUTURE",
                "event": {
                    "summary": "Weekly sync",
                    "dtstart": "2026-11-02T08:30:00-08:00",
                    "dtend": "2026-11-02T09:30:00-08:00",
                    "location": location,
                },
            },
        )

    # Room B is only this occurrence's, so sending it back keeps the series' Room A
    event = mock_save.call_args.args[0]
    assert event.object_id == "master3"
    payload = _saved_payload(mock_save)
    assert payload.get("location") == expected
    assert payload["start"]["dateTime"] == "2026-09-07T10:30:00"


async def test_update_all_day_series(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test update this and following - an all day series keeps its date."""

    event_name = "event2"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event2",
        f"calendar1/events/{event_name}",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": "calendar.test_calendar1",
                "uid": event_name,
                "recurrence_id": event_name,
                "recurrence_range": "THISANDFUTURE",
                "event": {
                    "summary": "Renamed all day series",
                    "dtstart": "2022-10-24",
                    "dtend": "2022-10-25",
                },
            },
        )

    payload = _saved_payload(mock_save)
    assert payload["isAllDay"] is True
    assert payload["start"]["dateTime"] == "2022-10-24T00:00:00"
    assert payload["end"]["dateTime"] == "2022-10-25T00:00:00"


async def test_create_recurring_event_unknown_time_zone(
    ws_client: ClientFixture,
    setup_update_integration,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test create recurring event - no Windows time zone for the HA time zone."""

    caplog.set_level(logging.DEBUG, logger=f"custom_components.{DOMAIN}")
    client = await ws_client()
    with (
        patch(
            f"custom_components.{DOMAIN}.integration.utils_integration.get_windows_tz",
            side_effect=ZoneInfoNotFoundError("Unknown"),
        ),
        patch("O365.calendar.Event.save", autospec=True) as mock_save,
    ):
        await client.cmd_result(
            "create",
            {
                "entity_id": "calendar.test_calendar1",
                "event": {
                    "summary": "Gym",
                    "dtstart": "2099-01-16T18:00:00",
                    "dtend": "2099-01-16T19:00:00",
                    "rrule": "FREQ=DAILY;COUNT=5",
                },
            },
        )

    event = mock_save.call_args.args[0]
    recurrence_range = event.recurrence.to_api_data()["range"]
    assert recurrence_range["startDate"] == "2099-01-16"
    assert recurrence_range["recurrenceTimeZone"] == "UTC"
    assert "recurrence time zone left unchanged" in caplog.text


async def test_create_event_with_location(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test create event - HA service sends the location."""

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await hass.services.async_call(
            CALENDAR_DOMAIN,
            CREATE_EVENT_SERVICE,
            {
                "entity_id": "calendar.test_calendar1",
                "summary": "Dentist",
                "location": "Dentist, Main St 1",
                "start_date_time": "2022-03-22T20:00:00.000Z",
                "end_date_time": "2022-03-22T22:00:00.000Z",
            },
            blocking=True,
            return_response=False,
        )

    event = mock_save.call_args.args[0]
    assert event.to_api_data()["location"] == {"displayName": "Dentist, Main St 1"}


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("Test Location", None),
        ("Room 2", {"displayName": "Room 2"}),
        ("", {"displayName": ""}),
    ],
)
async def test_update_event_ui_location(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
    location,
    expected,
) -> None:
    """Test update event - HA API call sends the location only when it changed."""

    event_name = "event3"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event_categories",
        f"calendar1/events/{event_name}",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": "calendar.test_calendar1",
                "uid": event_name,
                "event": {
                    "summary": "Holiday",
                    "dtstart": "2026-03-22",
                    "dtend": "2026-03-23",
                    "location": location,
                },
            },
        )

    # An unchanged name is left out, so Graph keeps the full location
    payload = _saved_payload(mock_save)
    assert payload.get("location") == expected
    assert payload["subject"] == "Holiday"


async def test_create_monthly_event_on_day_of_month(
    ws_client: ClientFixture,
    setup_update_integration,
) -> None:
    """Test create monthly event - HA API call keeps the day of the month asked for."""

    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "create",
            {
                "entity_id": "calendar.test_calendar1",
                "event": {
                    "summary": "Pay rent",
                    "dtstart": "2027-02-28",
                    "dtend": "2027-03-01",
                    "rrule": "FREQ=MONTHLY;BYMONTHDAY=-1",
                },
            },
        )

    # Outlook's last day of the month is the last of any day of the week
    recurrence = mock_save.call_args.args[0].recurrence.to_api_data()
    pattern = recurrence["pattern"]
    assert pattern["type"] == "relativeMonthly"
    assert pattern["index"] == "last"
    assert sorted(pattern["daysOfWeek"]) == [
        "friday",
        "monday",
        "saturday",
        "sunday",
        "thursday",
        "tuesday",
        "wednesday",
    ]
    assert recurrence["range"]["startDate"] == "2027-02-28"

    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "create",
            {
                "entity_id": "calendar.test_calendar1",
                "event": {
                    "summary": "Pay rent",
                    "dtstart": "2027-02-03",
                    "dtend": "2027-02-04",
                    "rrule": "FREQ=MONTHLY;BYMONTHDAY=15",
                },
            },
        )

    pattern = mock_save.call_args.args[0].recurrence.to_api_data()["pattern"]
    assert pattern == {"type": "absoluteMonthly", "interval": 1, "dayOfMonth": 15}


async def test_create_weekly_event_without_byday(
    ws_client: ClientFixture,
    setup_update_integration,
) -> None:
    """Test create weekly event - HA API call without BYDAY repeats on the start day."""

    client = await ws_client()
    with patch("O365.calendar.Event.save", autospec=True) as mock_save:
        await client.cmd_result(
            "create",
            {
                "entity_id": "calendar.test_calendar1",
                "event": {
                    "summary": "Gym",
                    "dtstart": "2099-01-16T18:00:00",
                    "dtend": "2099-01-16T19:00:00",
                    "rrule": "FREQ=WEEKLY;COUNT=4",
                },
            },
        )

    # 18:00 on Friday in US/Pacific is already Saturday in UTC
    recurrence = mock_save.call_args.args[0].recurrence.to_api_data()
    assert recurrence["pattern"] == {
        "type": "weekly",
        "interval": 1,
        "daysOfWeek": ["friday"],
        "firstDayOfWeek": "sunday",
    }
    assert recurrence["range"]["numberOfOccurrences"] == 4


def _saved_recurrence(mock_save):
    """Get the recurrence that saving the event sends to Graph, anchored on its date."""
    recurrence = mock_save.call_args.args[0].recurrence.to_api_data()
    assert recurrence["range"]["startDate"] == "2022-10-24"
    return recurrence


def _saved_payload(mock_save):
    """Get the data that saving the patched event sends to Graph."""
    event = mock_save.call_args.args[0]
    return event.to_api_data(restrict_keys=event._track_changes)  # noqa: SLF001


async def test_delete_event(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
    requests_mock: Mocker,
) -> None:
    """Test delete event - MS365 service."""

    event_name = "event1"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{event_name}",
    )

    calendar_name = "calendar.test_calendar1"
    with patch("O365.calendar.Event.delete") as mock_delete:
        await hass.services.async_call(
            DOMAIN,
            "remove_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()
    assert mock_delete.called
    assert len(listener_setup.events) == 1
    assert listener_setup.events[0].event_type == f"{DOMAIN}_remove_calendar_event"


async def test_delete_event_no_perms(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test delete event - no perms."""
    event_name = "event1"
    calendar_name = "calendar.test_calendar1"
    failed_perm = "calendar.failed_perm"
    with (
        patch(
            f"custom_components.{DOMAIN}.integration.calendar_integration.PERM_CALENDARS_READWRITE",
            failed_perm,
        ),
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "remove_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
            },
            blocking=True,
            return_response=False,
        )

    assert str(exc_info.value) == f"Not authorised requires permission: {failed_perm}"


async def test_delete_group_calendar(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test delete group calendar event - not allowed."""
    event_name = "event1"
    calendar_name = "calendar.test_calendar2"
    with (
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "remove_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
            },
            blocking=True,
            return_response=False,
        )

    assert (
        str(exc_info.value)
        == f"O365 Python does not have capability to update/respond to group calendar events: {calendar_name}"
    )


async def test_delete_recurring_event(
    ws_client: ClientFixture,
    setup_update_integration,
    requests_mock: Mocker,
) -> None:
    """Test delete recurring event - HA API call."""

    calendar_name = "calendar.test_calendar1"
    event_name = "event2"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event2",
        f"calendar1/events/{event_name}",
    )
    client = await ws_client()
    with patch("O365.calendar.Event.delete") as mock_delete:
        await client.cmd_result(
            "delete",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    assert mock_delete.called


async def test_respond_event(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
    requests_mock: Mocker,
) -> None:
    """Test respond to an event."""

    event_name = "event1"
    mock_call(
        requests_mock,
        URL.CALENDARS,
        "calendar1_event1",
        f"calendar1/events/{event_name}",
    )

    calendar_name = "calendar.test_calendar1"
    with patch("O365.calendar.Event.accept_event") as mock_accept_event:
        await hass.services.async_call(
            DOMAIN,
            "respond_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "response": "Accept",
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()
    assert mock_accept_event.called
    assert len(listener_setup.events) == 1
    assert listener_setup.events[0].event_type == f"{DOMAIN}_respond_calendar_event"

    with patch("O365.calendar.Event.accept_event") as mock_tentative_event:
        await hass.services.async_call(
            DOMAIN,
            "respond_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "response": "Tentative",
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()
    assert mock_tentative_event.called
    assert len(listener_setup.events) == 2

    with patch("O365.calendar.Event.decline_event") as mock_decline_event:
        await hass.services.async_call(
            DOMAIN,
            "respond_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "response": "Decline",
            },
            blocking=True,
            return_response=False,
        )
    await hass.async_block_till_done()
    assert mock_decline_event.called
    assert len(listener_setup.events) == 3


async def test_respond_group_calendar(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test respond to group event - not allowed."""
    event_name = "event1"
    calendar_name = "calendar.test_calendar2"
    with (
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "respond_calendar_event",
            {
                "entity_id": calendar_name,
                "event_id": event_name,
                "response": "Decline",
            },
            blocking=True,
            return_response=False,
        )

    assert (
        str(exc_info.value)
        == f"O365 Python does not have capability to update/respond to group calendar events: {calendar_name}"
    )


async def test_create_event_not_editable(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test create event - not editable (e.g. Birthday)."""

    calendar_name = "calendar.test_calendar3"
    with (
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "create_calendar_event",
            {
                "entity_id": calendar_name,
                "subject": "Department Party",
                "body": "Meeting to provide technical review for 'Phoenix' design.",
                "start": "2022-03-22T20:00:00.000Z",
                "end": "2022-03-23T22:00:00.000Z",
                "attendees": [{"email": "example@example.com", "type": "Required"}],
                "is_all_day": True,
            },
            blocking=True,
            return_response=False,
        )
    assert str(exc_info.value) == "Calendar - Calendar3 - is not editable"
