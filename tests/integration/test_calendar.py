# pylint: disable=unused-argument,line-too-long,wrong-import-order
"""Test main calendar testing."""

import logging
from copy import deepcopy
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from requests.exceptions import HTTPError
from requests_mock import Mocker
from zoneinfo import ZoneInfo

from ..helpers.mock_config_entry import MS365MockConfigEntry
from ..helpers.utils import check_entity_state, utcnow
from .const_integration import DOMAIN, FULL_INIT_ENTITY_NO
from .data_integration.state import BASE_STATE_CAL1, BASE_STATE_CAL2
from .helpers_integration.mocks import MS365MOCKS
from .helpers_integration.utils_integration import update_options, yaml_setup

START_BASE = datetime(2020, 1, 1, 0, 0, 0, tzinfo=ZoneInfo(key="UTC"))
END_BASE = datetime(2020, 1, 2, 23, 59, 59, tzinfo=ZoneInfo(key="UTC"))
START_ALL_DAY_BASE = date(2020, 1, 1)
END_ALL_DAY_BASE = date(2020, 1, 2)


async def test_get_data(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test get data."""
    logging.disable(logging.WARNING)
    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO

    check_entity_state(
        hass, "calendar.test_calendar1", "on", _adjust_date(BASE_STATE_CAL1)
    )
    check_entity_state(
        hass, "calendar.test_calendar2", "off", _adjust_date(BASE_STATE_CAL2, 1)
    )


async def test_one_not_tracked(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test one calendar not tracked."""

    await update_options(hass, base_config_entry)

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == 1


async def test_perms_error(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test permissions error."""

    with patch(
        f"custom_components.{DOMAIN}.integration.calendar_integration.MS365CalendarData.async_calendar_data_init",
        side_effect=HTTPError(),
    ):
        await update_options(hass, base_config_entry)

    assert "No permission for calendar" in caplog.text


async def test_fetch_error(
    hass: HomeAssistant,
    setup_base_integration,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test error fetching data."""
    with patch(
        f"custom_components.{DOMAIN}.integration.calendar_integration.MS365CalendarData.async_update_data",
        side_effect=HTTPError(),
    ):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert "Error getting calendar events for data" in caplog.text

    with patch(
        f"custom_components.{DOMAIN}.integration.calendar_integration.MS365CalendarData.async_update_data",
        side_effect=HTTPError(),
    ):
        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert "Repeat error - Error getting calendar events for data" in caplog.text


async def test_get_calendar_error(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    caplog: pytest.LogCaptureFixture,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test error when getting calendar."""
    MS365MOCKS.standard_mocks(requests_mock)

    base_config_entry.add_to_hass(hass)
    with patch(
        "O365.calendar.Schedule.get_calendar",
        side_effect=HTTPError(),
    ):
        await hass.config_entries.async_setup(base_config_entry.entry_id)
        await hass.async_block_till_done()

    assert "Error getting calendar" in caplog.text


async def test_no_events(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test calendar with not events."""
    MS365MOCKS.no_events_mocks(requests_mock)

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    check_entity_state(hass, "calendar.test_calendar1", "off", data_length=0)


async def test_filter_events(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test filtering of events."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_exclude")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    check_entity_state(hass, "calendar.test_calendar1", "on", data_length=1)


async def test_search_events(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test searching for events."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_search")

    base_config_entry.add_to_hass(hass)
    with patch("O365.calendar.Calendar.get_events") as get_events:
        await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert get_events.called
    assert "contains(subject, 'event 1')" in str(get_events.call_args_list)


async def test_sensitivity_exclude(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test filtering on sensitivity."""

    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_sensitivity")

    base_config_entry.add_to_hass(hass)

    with patch("O365.calendar.Calendar.get_events") as get_events:
        await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert get_events.called
    assert "sensitivity ne 'private'" in str(get_events.call_args_list)


@pytest.mark.parametrize(
    "setup_base_integration", [{"method_name": "all_day_event_mocks"}], indirect=True
)
async def test_all_day_event(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test all day event."""
    check_entity_state(
        hass, "calendar.test_calendar1", "on", attributes={"message": "Test all day"}
    )


@pytest.mark.parametrize(
    "setup_base_integration", [{"method_name": "started_event_mocks"}], indirect=True
)
async def test_started_event(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test started event."""

    check_entity_state(
        hass, "calendar.test_calendar1", "on", attributes={"message": "Test started"}
    )


@pytest.mark.parametrize(
    "setup_base_integration",
    [{"method_name": "not_started_event_mocks"}],
    indirect=True,
)
async def test_not_started_event(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test not started event."""

    check_entity_state(
        hass,
        "calendar.test_calendar1",
        "off",
        attributes={"message": "Test not started"},
    )


def _adjust_date(data, adddays=0):
    new_data = deepcopy(data)
    start = (utcnow() + timedelta(days=adddays)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = (utcnow() + timedelta(days=1 + adddays)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    start_all_day = start.date()
    end_all_day = end.date()
    for item in new_data:
        if item["start"] == START_BASE:
            item["start"] = start
        if item["end"] == END_BASE:
            item["end"] = end
        if item["start"] == START_ALL_DAY_BASE:
            item["start"] = start_all_day
        if item["end"] == END_ALL_DAY_BASE:
            item["end"] = end_all_day

    return new_data
