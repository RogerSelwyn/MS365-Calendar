# pylint: disable=unused-argument,line-too-long,wrong-import-order
"""Test file management."""

import pytest
from homeassistant.core import HomeAssistant
from requests_mock import Mocker

from ..helpers.mock_config_entry import MS365MockConfigEntry
from .helpers_integration.mocks import MS365MOCKS
from .helpers_integration.utils_integration import check_yaml_file_contents, yaml_setup


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
    """Test for corrupt yaml content."""
    # logging.disable(logging.WARNING)
    MS365MOCKS.standard_mocks(requests_mock)
    yaml_setup(tmp_path, "ms365_calendars_corrupt")

    base_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Invalid Data - duplicate entries may be created" in caplog.text
