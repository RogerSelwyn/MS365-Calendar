"""Schema for MS365 Integration."""

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.data_entry_flow import section

from .const import (
    CONF_ALT_AUTH_METHOD,
    CONF_API_COUNTRY,
    CONF_API_OPTIONS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENTITY_NAME,
    CONF_URL,
    CountryOptions,
)

CONFIG_SCHEMA = {
    vol.Required(CONF_ENTITY_NAME): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_CLIENT_ID): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_CLIENT_SECRET): vol.All(cv.string, vol.Strip),
    vol.Optional(CONF_ALT_AUTH_METHOD, default=False): cv.boolean,
    vol.Required(CONF_API_OPTIONS): section(
        vol.Schema(
            {
                vol.Required(CONF_API_COUNTRY, default=CountryOptions.DEFAULT): vol.In(
                    CountryOptions
                )
            }
        ),
        {"collapsed": True},
    ),
}

REQUEST_AUTHORIZATION_DEFAULT_SCHEMA = {vol.Required(CONF_URL): cv.string}
