"""Main initialisation code."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.network import get_url
from oauthlib.oauth2.rfc6749.errors import InvalidClientError

from .classes.api import MS365Account, MS365Token
from .classes.config_entry import MS365ConfigEntry, MS365Data
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENTITY_NAME,
    CONF_SHARED_MAILBOX,
    SECRET_EXPIRED,
    TOKEN_DELETED,
    TOKEN_ERROR,
    TOKEN_EXPIRED,
    TOKEN_FILE_EXPIRED,
    TOKEN_FILE_MISSING,
)
from .integration import setup_integration
from .integration.const_integration import DOMAIN, PLATFORMS
from .integration.permissions_integration import Permissions

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
    token_backend = MS365Token(hass, entry.data)
    perms = Permissions(hass, entry.data, token_backend)
    ha_account = MS365Account(perms, entry.data)
    if token_backend.check_token_exists():
        error = (
            await hass.async_add_executor_job(
                ha_account.try_authentication, credentials, main_resource, entity_name
            )
            or await perms.async_check_authorizations()
        )
    else:
        error = TOKEN_FILE_MISSING

    if not error:
        _LOGGER.debug("Do setup")
        check_token = await _async_check_token(hass, ha_account.account, entity_name)
        if check_token:
            coordinator, sensors, platforms = await setup_integration.async_do_setup(
                hass, entry, ha_account.account
            )
            entry.runtime_data = MS365Data(
                perms,
                ha_account,
                coordinator,
                sensors,
                entry.options,
            )
            await hass.config_entries.async_forward_entry_setups(entry, platforms)
            entry.async_on_unload(entry.add_update_listener(async_reload_entry))
            return True
        else:
            error = TOKEN_FILE_EXPIRED

    url = f"{get_url(hass)}/config/integrations/integration/{DOMAIN}"
    ir.async_create_issue(
        hass,
        DOMAIN,
        error,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=error,
        translation_placeholders={
            "domain": DOMAIN,
            "url": url,
            CONF_ENTITY_NAME: entry.data.get(CONF_ENTITY_NAME),
        },
    )
    return False


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: MS365ConfigEntry
) -> bool:
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    # if config_entry.version > 2:
    #     # This shouldn't happen since we are at v2
    #     return False

    if config_entry.version == 1:
        # Delete the token file ready for re-auth
        new_data = {**config_entry.data}
        token_backend = MS365Token(hass, config_entry.data)
        await hass.async_add_executor_job(token_backend.delete_token)
        _LOGGER.warning(
            TOKEN_DELETED,
            token_backend.token_filename,
        )
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=0, version=2
        )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MS365ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: MS365ConfigEntry) -> None:
    """Handle options update - only reload if the options have changed."""
    if entry.runtime_data.options != entry.options:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: MS365ConfigEntry) -> None:
    """Handle removal of an entry."""
    token_backend = MS365Token(hass, entry.data)
    await hass.async_add_executor_job(token_backend.delete_token)
    if not hasattr(setup_integration, "async_integration_remove_entry"):
        return
    await setup_integration.async_integration_remove_entry(hass, entry)


async def _async_check_token(hass, account, entity_name):
    try:
        await hass.async_add_executor_job(account.get_current_user_data)
        return True
    except InvalidClientError as err:
        if "client secret" in err.description and "expired" in err.description:
            _LOGGER.warning(SECRET_EXPIRED, entity_name)
        else:
            _LOGGER.warning(TOKEN_ERROR, entity_name, err.description)
        return False
    except RuntimeError as err:
        if "Refresh token operation failed: invalid_grant" in err.args:
            _LOGGER.warning(TOKEN_EXPIRED, entity_name)
            return False
        raise err
