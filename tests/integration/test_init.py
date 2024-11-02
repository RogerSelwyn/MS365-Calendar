# pylint: disable=unused-argument
"""Test setup process."""

from unittest.mock import patch

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_CALENDAR_LIST,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_TRACK_NEW_CALENDAR,
)

from ..helpers.mock_config_entry import MS365MockConfigEntry
from .const_integration import UPDATE_CALENDAR_LIST


async def test_reload(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test for reload."""

    result = await hass.config_entries.options.async_init(base_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TRACK_NEW_CALENDAR: True,
            CONF_CALENDAR_LIST: UPDATE_CALENDAR_LIST,
        },
    )
    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload"
    ) as mock_async_reload:
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "Calendar1",
                CONF_HOURS_FORWARD_TO_GET: 24,
                CONF_HOURS_BACKWARD_TO_GET: 0,
            },
        )
    assert mock_async_reload.called
