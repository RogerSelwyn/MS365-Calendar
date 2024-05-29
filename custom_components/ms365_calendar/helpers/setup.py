"""Do configuration setup."""

import logging

from homeassistant.helpers import discovery

from ..const import (
    CONF_ACCOUNT,
    CONF_ACCOUNT_NAME,
    CONF_CLIENT_ID,
    CONF_ENABLE_UPDATE,
    CONF_PERMISSIONS,
    CONF_TRACK_NEW_CALENDAR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def do_setup(hass, config, account, account_name, perms):
    """Run the setup after we have everything configured."""
    enable_update = config.get(CONF_ENABLE_UPDATE, False)

    account_config = {
        CONF_CLIENT_ID: config.get(CONF_CLIENT_ID),
        CONF_ACCOUNT: account,
        CONF_ENABLE_UPDATE: enable_update,
        CONF_TRACK_NEW_CALENDAR: config.get(CONF_TRACK_NEW_CALENDAR, True),
        CONF_ACCOUNT_NAME: config.get(CONF_ACCOUNT_NAME, ""),
        CONF_PERMISSIONS: perms,
    }
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][account_name] = account_config

    _load_platforms(hass, account_name, config)


def _load_platforms(hass, account_name, config):
    hass.async_create_task(
        discovery.async_load_platform(
            hass, "calendar", DOMAIN, {CONF_ACCOUNT_NAME: account_name}, config
        )
    )
