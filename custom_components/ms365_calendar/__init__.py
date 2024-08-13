"""Main initialisation code."""

import functools as ft
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from O365 import Account, FileSystemTokenBackend
from oauthlib.oauth2.rfc6749.errors import InvalidClientError

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENTITY_NAME,
    CONF_SHARED_MAILBOX,
    CONST_UTC_TIMEZONE,
)
from .helpers.config_entry import MS365ConfigEntry, MS365Data
from .integration.const_integration import DOMAIN, PLATFORMS
from .integration.permissions_integration import Permissions
from .integration.setup_integration import async_do_setup

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: MS365ConfigEntry):
    """Set up a config entry."""

    credentials = (
        entry.data.get(CONF_CLIENT_ID),
        entry.data.get(CONF_CLIENT_SECRET),
    )
    entity_name = entry.data.get(CONF_ENTITY_NAME)
    main_resource = entry.data.get(CONF_SHARED_MAILBOX)

    _LOGGER.debug("Permissions setup")
    perms = Permissions(hass, entry.data)
    permissions, failed_permissions = await perms.async_check_authorizations()  # pylint: disable=unused-variable
    if permissions is True:
        account, is_authenticated = await _async_try_authentication(
            hass, perms, credentials, main_resource
        )
    else:
        is_authenticated = False
        account = None

    if is_authenticated and permissions is True:
        _LOGGER.debug("Do setup")
        check_token = await _async_check_token(hass, account, entity_name)
        if check_token:
            coordinator, sensors, platforms = await async_do_setup(hass, entry, account)
            entry.runtime_data = MS365Data(
                perms, account, coordinator, sensors, entry.options
            )
            await hass.config_entries.async_forward_entry_setups(entry, platforms)
            entry.async_on_unload(entry.add_update_listener(async_reload_entry))
            return True
    else:
        ir.async_create_issue(
            hass,
            DOMAIN,
            permissions,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=permissions,
            translation_placeholders={
                "domain": DOMAIN,
                CONF_ENTITY_NAME: entry.data.get(CONF_ENTITY_NAME),
            },
        )
        return False


async def async_unload_entry(hass: HomeAssistant, entry: MS365ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: MS365ConfigEntry) -> None:
    """Handle options update - only reload if the options have changed."""
    if entry.runtime_data.options != entry.options:
        await hass.config_entries.async_reload(entry.entry_id)


async def _async_try_authentication(hass, perms, credentials, main_resource):
    _LOGGER.debug("Setup token")
    token_backend = await hass.async_add_executor_job(
        ft.partial(
            FileSystemTokenBackend,
            token_path=perms.token_path,
            token_filename=perms.token_filename,
        )
    )
    _LOGGER.debug("Setup account")
    account = await hass.async_add_executor_job(
        ft.partial(
            Account,
            credentials,
            token_backend=token_backend,
            timezone=CONST_UTC_TIMEZONE,
            main_resource=main_resource,
        )
    )

    return account, account.is_authenticated


async def _async_check_token(hass, account, entity_name):
    try:
        await hass.async_add_executor_job(account.get_current_user)
        return True
    except InvalidClientError as err:
        if "client secret" in err.description and "expired" in err.description:
            _LOGGER.warning(
                (
                    "Client Secret expired for account: %s. "
                    + "Create new Client Secret in Entra ID App Registration."
                ),
                entity_name,
            )
        else:
            _LOGGER.warning(
                "Token error for account: %s. Error - %s", entity_name, err.description
            )
        return False
