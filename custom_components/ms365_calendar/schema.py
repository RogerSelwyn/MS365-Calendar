"""Schema for MS365 Integration."""

import probatio

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
    probatio.Required(CONF_ENTITY_NAME): probatio.All(cv.string, probatio.Strip),
    probatio.Required(CONF_CLIENT_ID): probatio.All(cv.string, probatio.Strip),
    probatio.Required(CONF_ENVIRONMENT_SECRET, default=False): BooleanSelector(),
    data_entry_flow.Required(
        CONF_CLIENT_SECRET, visible={"field": CONF_ENVIRONMENT_SECRET, "value": False}
    ): probatio.All(cv.string, probatio.Strip),
    data_entry_flow.Required(
        CONF_CLIENT_SECRET_VARIABLE,
        default=MS365_CLIENT_SECRET,
        visible={"field": CONF_ENVIRONMENT_SECRET, "value": True},
    ): probatio.All(cv.string, probatio.Strip),
    probatio.Optional(CONF_ALT_AUTH_METHOD, default=False): BooleanSelector(),
    probatio.Required(CONF_API_OPTIONS): section(
        probatio.Schema(
            {
                probatio.Required(
                    CONF_API_COUNTRY, default=CountryOptions.DEFAULT
                ): probatio.In(CountryOptions),
                probatio.Optional(CONF_TENANT_ID, default=""): probatio.All(
                    cv.string, probatio.Strip
                ),
            }
        ),
        {"collapsed": True},
    ),
}

REQUEST_AUTHORIZATION_DEFAULT_SCHEMA = {probatio.Required(CONF_URL): cv.string}
