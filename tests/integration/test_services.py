# pylint: disable=unused-argument,line-too-long,wrong-import-order
"""Test service usage."""

from datetime import datetime
from unittest.mock import patch

import pytest
from homeassistant.components.calendar import CREATE_EVENT_SERVICE, SERVICE_GET_EVENTS
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from requests_mock import Mocker
from voluptuous.error import MultipleInvalid
from zoneinfo import ZoneInfo

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


async def test_get_events(
    hass: HomeAssistant,
    setup_base_integration,
) -> None:
    """Test get events - HA Service."""
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
    await hass.async_block_till_done()
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

    assert (
        str(exc_info.value)
        == f"Not authorisied to Calendar1 calendar event - requires permission: {failed_perm}"
    )


async def test_update_event(
    hass: HomeAssistant,
    setup_update_integration,
    listener_setup: ListenerSetupData,
    requests_mock: Mocker,
) -> None:
    """Test update event - MS365 service"""

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

    assert (
        str(exc_info.value)
        == f"Not authorisied to Calendar1 calendar event - requires permission: {failed_perm}"
    )


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
    with patch("O365.calendar.Event.save") as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2024-10-24T07:00:00.0000000",
                    "dtend": "2024-10-24T07:30:00.0000000",
                    "rrule": "COUNT=5;FREQ=DAILY",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    assert mock_save.called

    with patch("O365.calendar.Event.save") as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2024-10-24T07:00:00.0000000",
                    "dtend": "2024-10-24T07:30:00.0000000",
                    "rrule": "UNTIL=20990101T010101;FREQ=WEEKLY;BYDAY=MO",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    assert mock_save.called

    with patch("O365.calendar.Event.save") as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2024-10-24T07:00:00.0000000",
                    "dtend": "2024-10-24T07:30:00.0000000",
                    "rrule": "UNTIL=20990101T010101;FREQ=MONTHLY",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    assert mock_save.called

    with patch("O365.calendar.Event.save") as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2024-10-24T07:00:00.0000000",
                    "dtend": "2024-10-24T07:30:00.0000000",
                    "rrule": "FREQ=MONTHLY;BYDAY=+4FR",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    assert mock_save.called

    with patch("O365.calendar.Event.save") as mock_save:
        await client.cmd_result(
            "update",
            {
                "entity_id": calendar_name,
                "uid": event_name,
                "event": {
                    "summary": "Festival International de Jazz de Montreal",
                    "dtstart": "2024-10-24T07:00:00.0000000",
                    "dtend": "2024-10-24T07:30:00.0000000",
                    "rrule": "UNTIL=20990101T010101;FREQ=YEARLY",
                },
                "recurrence_range": "some range",
                "recurrence_id": event_name,
            },
        )

    assert mock_save.called


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

    assert (
        str(exc_info.value)
        == f"Not authorisied to Calendar1 calendar event - requires permission: {failed_perm}"
    )


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
