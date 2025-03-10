"""Calendar processing."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .classes.config_entry import MS365ConfigEntry
from .integration.calendar_integration import async_integration_setup_entry

PARALLEL_UPDATES = 8


async def async_setup_entry(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    entry: MS365ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MS365 platform."""

    return await async_integration_setup_entry(hass, entry, async_add_entities)
