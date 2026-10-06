# pylint: disable=unused-argument,line-too-long,wrong-import-order
"""Test calendar entity setup and removal."""

import pytest
from requests.exceptions import RetryError
from requests_mock import Mocker

from homeassistant.components.calendar import (
    DOMAIN as CALENDAR_DOMAIN,
    CalendarEntityFeature,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_DEVICE_ID,
)

from ..helpers.mock_config_entry import MS365MockConfigEntry
from .const_integration import DOMAIN, FULL_INIT_ENTITY_NO, URL
from .helpers_integration.mocks import MS365MOCKS
from .helpers_integration.utils_integration import update_options, yaml_setup

CALENDAR1_VIEW = f"{URL.CALENDARS.value}/calendar1/calendarView"
NOT_FOUND = {
    "error": {
        "code": "ErrorItemNotFound",
        "message": "The specified object was not found in the store.",
    }
}


async def test_shared_name(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test entities with the same name each show their own calendar."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_same_name")

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        entity_registry.async_get("calendar.test_calendar1").unique_id
        == "calendar1_test_Calendar1"
    )
    assert (
        entity_registry.async_get("calendar.test_calendar3").unique_id
        == "calendar3_test_Calendar3"
    )

    state = hass.states.get("calendar.test_calendar1")
    assert state.attributes["friendly_name"] == "Calendar"
    assert [event["summary"] for event in state.attributes["data"]] == [
        "Test event 1 calendar1",
        "Test event 2 calendar1",
    ]
    state = hass.states.get("calendar.test_calendar3")
    assert state.attributes["friendly_name"] == "Calendar"
    assert [event["summary"] for event in state.attributes["data"]] == [
        "Test event 1 calendar3"
    ]


async def test_shared_name_calendar_error(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a failed calendar does not show another calendar with the same name."""
    MS365MOCKS.standard_mocks(requests_mock)
    requests_mock.get(
        f"{URL.CALENDARS.value}/calendar3", status_code=404, json=NOT_FOUND
    )
    yaml_setup(tmp_path, "ms365_calendars_same_name")

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Error getting calendar - calendar3 - calendar.test_calendar3" in caplog.text
    assert hass.states.get("calendar.test_calendar3") is None
    state = hass.states.get("calendar.test_calendar1")
    assert [event["summary"] for event in state.attributes["data"]] == [
        "Test event 1 calendar1",
        "Test event 2 calendar1",
    ]


async def test_shared_name_failed_sync(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test a failed sync keeps the events of its own entity on a shared calendar."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_same_calendar")

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinators = {
        coordinator.entity[CONF_DEVICE_ID]: coordinator
        for coordinator in base_config_entry.runtime_data.coordinator
    }
    await coordinators["Calendar1"].async_refresh()
    requests_mock.get(CALENDAR1_VIEW, status_code=503)
    await coordinators["Calendar1_wall"].async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get("calendar.test_calendar1_wall")
    assert state.attributes["sync_state"] == "problem"
    assert [event["summary"] for event in state.attributes["data"]] == [
        "Test event 1 calendar1"
    ]
    state = hass.states.get("calendar.test_calendar1")
    assert state.attributes["sync_state"] == "ok"
    assert [event["summary"] for event in state.attributes["data"]] == [
        "Test event 1 calendar1",
        "Test event 2 calendar1",
    ]


async def test_deselect_renamed_calendar(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test an entity the user renamed is removed when its calendar is deselected."""
    entity_registry.async_update_entity(
        "calendar.test_calendar2", new_entity_id="calendar.renamed"
    )
    await hass.async_block_till_done()

    await update_options(hass, base_config_entry)
    await hass.async_block_till_done()

    assert entity_registry.async_get("calendar.renamed") is None
    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert [entity.entity_id for entity in entities] == ["calendar.test_calendar1"]


async def test_deleted_renamed_calendar(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test an entity the user renamed is removed when its calendar is deleted."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_delete")
    base_config_entry.add_to_hass(hass)
    entry = entity_registry.async_get_or_create(
        CALENDAR_DOMAIN,
        DOMAIN,
        "delete_calendar_test_Delete calendar",
        config_entry=base_config_entry,
    )
    entity_registry.async_update_entity(entry.entity_id, new_entity_id="calendar.renamed")

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert entity_registry.async_get("calendar.renamed") is None
    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO


async def test_group_calendar_error(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a group calendar that cannot be read is not set up and never polled."""
    MS365MOCKS.standard_mocks(requests_mock)
    requests_mock.get(
        f"{URL.GROUP_CALENDARS.value}/calendar2/calendar",
        status_code=404,
        json=NOT_FOUND,
    )

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        caplog.text.count(
            "Error getting group calendar - group:calendar2 - calendar.test_calendar2"
        )
        == 1
    )
    assert hass.states.get("calendar.test_calendar2") is None
    assert hass.states.get("calendar.test_calendar1") is not None
    assert not [
        request
        for request in requests_mock.request_history
        if "/groups/calendar2/calendar/calendarView" in request.url
    ]


async def test_group_calendar_busy(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test a group calendar is kept when MS Graph is busy, not when it is missing."""
    MS365MOCKS.standard_mocks(requests_mock)
    requests_mock.get(
        f"{URL.GROUP_CALENDARS.value}/calendar2/calendar",
        exc=RetryError("Max retries exceeded"),
    )
    requests_mock.get(
        f"{URL.GROUP_CALENDARS.value}/calendar4/calendar",
        status_code=404,
        json=NOT_FOUND,
    )
    yaml_setup(tmp_path, "ms365_calendars_group")

    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("calendar.test_calendar2")
    assert state is not None
    assert [event["summary"] for event in state.attributes["data"]] == [
        "Test event calendar2"
    ]
    assert "Error getting group calendar - group:calendar2" not in caplog.text
    assert (
        "Error getting group calendar - group:calendar4 - calendar.test_calendar4"
        in caplog.text
    )
    assert hass.states.get("calendar.test_calendar4") is None


async def test_group_calendar_features(
    hass: HomeAssistant,
    setup_update_integration,
) -> None:
    """Test a group calendar only offers to create events."""
    state = hass.states.get("calendar.test_calendar2")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == CalendarEntityFeature.CREATE_EVENT

    state = hass.states.get("calendar.test_calendar1")
    assert state.attributes[ATTR_SUPPORTED_FEATURES] == (
        CalendarEntityFeature.CREATE_EVENT
        | CalendarEntityFeature.DELETE_EVENT
        | CalendarEntityFeature.UPDATE_EVENT
    )
