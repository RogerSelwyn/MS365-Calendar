"""Utilities processes."""

import os

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id

from ..const import (
    AUTH_ERROR_ENVIRONMENT_VARIABLE_EMPTY,
    AUTH_ERROR_ENVIRONMENT_VARIABLE_INVALID,
    CONF_API_COUNTRY,
    CONF_API_OPTIONS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_CLIENT_SECRET_VARIABLE,
    CONF_ENVIRONMENT_SECRET,
    CONF_TENANT_ID,
    DEFAULT_TENANT_ID,
    CountryOptions,
)


def add_attribute_to_item(item, user_input, attribute):
    """Add an attribute to an item."""
    value = user_input.get(attribute)
    if value is not None and value != []:
        item[attribute] = value
    elif attribute in item:
        del item[attribute]


def build_entity_id(hass: HomeAssistant, entity_id_format, name):
    """Build an entity ID."""
    return async_generate_entity_id(
        entity_id_format,
        name,
        hass=hass,
    )


def get_country(entry_data):
    """Get the country from entry_data."""
    country = CountryOptions.DEFAULT
    if entry_data.get(CONF_API_OPTIONS):
        country = entry_data[CONF_API_OPTIONS][CONF_API_COUNTRY]
    return country


def get_tenant_id(entry_data):
    """Get the tenant_id from entry_data, defaulting to 'common'."""
    if entry_data.get(CONF_API_OPTIONS):
        tid = entry_data[CONF_API_OPTIONS].get(CONF_TENANT_ID, "")
        if tid.strip():
            return tid.strip()
    return DEFAULT_TENANT_ID


def create_issue_id(error, entry_id):
    """Create standard format issue id."""
    return f"{error}_{entry_id}"


def get_credentials(config):
    """Return the configured client credentials."""
    error = False
    client_secret = config.get(CONF_CLIENT_SECRET)
    if config.get(CONF_ENVIRONMENT_SECRET):
        environ_var = config.get(CONF_CLIENT_SECRET_VARIABLE)
        if environ_var in os.environ:
            client_secret = os.environ.get(environ_var)
            if not client_secret:
                error = AUTH_ERROR_ENVIRONMENT_VARIABLE_EMPTY
        else:
            error = AUTH_ERROR_ENVIRONMENT_VARIABLE_INVALID
    return (config.get(CONF_CLIENT_ID), client_secret), error


async def async_check_personal_account(hass: HomeAssistant, token_backend):
    """Check if account is a personal account."""
    account = await hass.async_add_executor_job(token_backend.token_backend.get_account)
    if account:
        tenant_id = account["home_account_id"].removeprefix(
            f"{account['local_account_id']}."
        )
        return tenant_id == "9188040d-6c67-4c5b-b112-36a304b66dad"
    return True
