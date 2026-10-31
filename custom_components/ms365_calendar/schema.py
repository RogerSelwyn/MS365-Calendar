"""Schema for MS365 Integration."""

import voluptuous as vol

from homeassistant.data_entry_flow import section
import homeassistant.helpers.config_validation as cv

from .const import (
    CLIENT_SECRET_SOURCE_ENVIRONMENT,
    CLIENT_SECRET_SOURCE_MANUAL,
    CONF_ALT_AUTH_METHOD,
    CONF_API_COUNTRY,
    CONF_API_OPTIONS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_CLIENT_SECRET_ENV_VAR,
    CONF_CLIENT_SECRET_SOURCE,
    CONF_ENTITY_NAME,
    CONF_TENANT_ID,
    CONF_URL,
    CountryOptions,
)

CONFIG_SCHEMA = {
    vol.Required(CONF_ENTITY_NAME): vol.All(cv.string, vol.Strip),
    vol.Required(CONF_CLIENT_ID): vol.All(cv.string, vol.Strip),
    vol.Required(
        CONF_CLIENT_SECRET_SOURCE, default=CLIENT_SECRET_SOURCE_ENVIRONMENT
    ): vol.In((CLIENT_SECRET_SOURCE_ENVIRONMENT, CLIENT_SECRET_SOURCE_MANUAL)),
    vol.Optional(CONF_ALT_AUTH_METHOD, default=False): cv.boolean,
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

CLIENT_SECRET_ENVIRONMENT_SCHEMA = {
    vol.Optional(CONF_CLIENT_SECRET_ENV_VAR, default="MS365_CLIENT_SECRET"): vol.All(
        cv.string, vol.Strip
    ),
}

CLIENT_SECRET_MANUAL_SCHEMA = {
    vol.Optional(CONF_CLIENT_SECRET, default=""): vol.All(cv.string, vol.Strip),
}

REQUEST_AUTHORIZATION_DEFAULT_SCHEMA = {vol.Required(CONF_URL): cv.string}
