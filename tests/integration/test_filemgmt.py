# pylint: disable=unused-argument,line-too-long,wrong-import-order
"""Test file management."""

import pytest
from requests_mock import Mocker

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..helpers.mock_config_entry import MS365MockConfigEntry
from .const_integration import FULL_INIT_ENTITY_NO
from .helpers_integration.mocks import MS365MOCKS
from .helpers_integration.utils_integration import check_yaml_file_contents, read_yaml_file, yaml_setup


async def test_base_filemgmt(
    tmp_path,
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test base file management."""

    check_yaml_file_contents(tmp_path, "ms365_calendars_base")


async def test_empty_file(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test for an empty yaml file."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_empty")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    check_yaml_file_contents(tmp_path, "ms365_calendars_base")


async def test_corrupt_file(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for corrupt yaml content (missing name)."""
    # logging.disable(logging.WARNING)
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_corrupt")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Invalid Data - duplicate entries may be created" in caplog.text


async def test_corrupt_file_2(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for corrupt yaml content (hanging hyphen)."""
    # logging.disable(logging.WARNING)
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_corrupt2")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Invalid Data - duplicate entries may be created" in caplog.text

    entities = er.async_entries_for_config_entry(entity_registry, base_config_entry.entry_id)
    assert len(entities) == FULL_INIT_ENTITY_NO


async def test_corrupt_file_3(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for corrupt yaml content (empty cal_id)."""
    # logging.disable(logging.WARNING)
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_corrupt3")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Invalid Data - duplicate entries may be created" in caplog.text

    entities = er.async_entries_for_config_entry(entity_registry, base_config_entry.entry_id)
    assert len(entities) == FULL_INIT_ENTITY_NO


async def test_deleted_file(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test for deleting yaml content."""
    # logging.disable(logging.WARNING)
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_delete")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    check_yaml_file_contents(tmp_path, "ms365_calendars_base")

    assert "Calendar deleted from" in caplog.text


async def test_deleted_file_sensitivity(
    tmp_path,
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test deleting yaml content keeps sensitivity_exclude as plain text."""
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_delete_sensitivity")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    calendars = read_yaml_file(tmp_path)
    assert [calendar["cal_id"] for calendar in calendars] == [
        "calendar1",
        "group:calendar2",
        "calendar3",
    ]
    assert calendars[0]["entities"][0]["sensitivity_exclude"] == ["private"]

    assert base_config_entry.state is ConfigEntryState.LOADED
