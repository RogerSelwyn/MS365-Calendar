"""Schema for MS365 Integration."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import (
    CONF_ACCOUNT_NAME,
    CONF_ALT_AUTH_METHOD,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SHARED_MAILBOX,  # noqa: F401
    CONF_URL,
)

CONFIG_SCHEMA = {
    vol.Required(CONF_ACCOUNT_NAME): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_CLIENT_ID): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_CLIENT_SECRET): vol.All(cv.string, vol.Strip),
    vol.Optional(CONF_ALT_AUTH_METHOD, default=False): cv.boolean,
}

REQUEST_AUTHORIZATION_DEFAULT_SCHEMA = {vol.Required(CONF_URL): cv.string}
