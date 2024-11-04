"""Utilities for MS365 testing."""

import shutil

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_CALENDAR_LIST,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_TRACK_NEW_CALENDAR,
    DOMAIN,
)

from ...const import STORAGE_LOCATION, TEST_DATA_INTEGRATION_LOCATION
from ...helpers.mock_config_entry import MS365MockConfigEntry
from ..const_integration import UPDATE_CALENDAR_LIST


def yaml_setup(tmp_path, infile):
    """Setup a yaml file"""
    fromfile = TEST_DATA_INTEGRATION_LOCATION / f"yaml/{infile}.yaml"
    tofile = tmp_path / STORAGE_LOCATION / f"{DOMAIN}s_test.yaml"
    shutil.copy(fromfile, tofile)


async def update_options(
    hass: HomeAssistant,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the options flow"""

    result = await hass.config_entries.options.async_init(base_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TRACK_NEW_CALENDAR: False,
            CONF_CALENDAR_LIST: UPDATE_CALENDAR_LIST,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Calendar1_Changed",
            CONF_HOURS_FORWARD_TO_GET: 48,
            CONF_HOURS_BACKWARD_TO_GET: -48,
            CONF_MAX_RESULTS: 5,
        },
    )


def check_yaml_file_contents(tmp_path, filename):
    """Check contents are what is expected."""
    path = tmp_path / STORAGE_LOCATION / f"{DOMAIN}s_test.yaml"
    with open(path, encoding="utf8") as file:
        created_yaml = file.read()
    path = TEST_DATA_INTEGRATION_LOCATION / f"yaml/{filename}.yaml"
    with open(path, encoding="utf8") as file:
        compare_yaml = file.read()
    assert created_yaml == compare_yaml
