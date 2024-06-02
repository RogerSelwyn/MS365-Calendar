"""Do configuration setup."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_do_setup(hass: HomeAssistant, entry: ConfigEntry, account):  # pylint: disable=unused-argument
    """Run the setup after we have everything configured."""

    return None, None
