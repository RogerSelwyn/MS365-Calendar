"""Schema for MS365 Integration."""

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.data_entry_flow import section
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import BooleanSelector

from .const import (
    CONF_ALT_AUTH_METHOD,
    CONF_API_COUNTRY,
    CONF_API_OPTIONS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_CLIENT_SECRET_VARIABLE,
    CONF_ENTITY_NAME,
    CONF_ENVIRONMENT_SECRET,
    CONF_TENANT_ID,
    CONF_URL,
    MS365_CLIENT_SECRET,
    CountryOptions,
)

CONFIG_SCHEMA = {
    vol.Required(CONF_ENTITY_NAME): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_CLIENT_ID): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_ENVIRONMENT_SECRET, default=False): BooleanSelector(),
    data_entry_flow.Required(
        CONF_CLIENT_SECRET, visible={"field": CONF_ENVIRONMENT_SECRET, "value": False}
    ): vol.All(cv.string, vol.Strip),
    data_entry_flow.Required(
        CONF_CLIENT_SECRET_VARIABLE,
        default=MS365_CLIENT_SECRET,
        visible={"field": CONF_ENVIRONMENT_SECRET, "value": True},
    ): vol.All(cv.string, vol.Strip),
    vol.Optional(CONF_ALT_AUTH_METHOD, default=False): BooleanSelector(),
    vol.Required(CONF_API_OPTIONS): section(
        vol.Schema(
            {
                vol.Required(CONF_API_COUNTRY, default=CountryOptions.DEFAULT): vol.In(
                    CountryOptions
                ),
                vol.Optional(CONF_TENANT_ID, default=""): vol.All(cv.string, vol.Strip),
            }
        ),
        {"collapsed": True},
    ),
}

REQUEST_AUTHORIZATION_DEFAULT_SCHEMA = {vol.Required(CONF_URL): cv.string}
