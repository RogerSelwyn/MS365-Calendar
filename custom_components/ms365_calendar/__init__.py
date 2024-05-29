"""Main initialisation code."""

import functools as ft
import json
import logging

import voluptuous as vol
import yaml
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from O365 import Account, FileSystemTokenBackend
from oauthlib.oauth2.rfc6749.errors import InvalidClientError

from .classes.permissions import Permissions
from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNT_CONF,
    CONF_ACCOUNT_NAME,
    CONF_ACCOUNTS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_FAILED_PERMISSIONS,
    CONF_SHARED_MAILBOX,
    CONST_PRIMARY,
    CONST_UTC_TIMEZONE,
    DOMAIN,
    TOKEN_FILE_MISSING,
)
from .helpers.setup import do_setup
from .schema import MULTI_ACCOUNT_SCHEMA

CONFIG_SCHEMA = vol.Schema({DOMAIN: MULTI_ACCOUNT_SCHEMA}, extra=vol.ALLOW_EXTRA)
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Set up the O365 platform."""
    _LOGGER.debug("Startup")
    conf = config.get(DOMAIN, {})

    accounts = MULTI_ACCOUNT_SCHEMA(conf)[CONF_ACCOUNTS]

    for account in accounts:
        await _async_setup_account(hass, account)

    _LOGGER.debug("Finish")
    return True


async def _async_setup_account(hass, account_conf):
    credentials = (
        account_conf.get(CONF_CLIENT_ID),
        account_conf.get(CONF_CLIENT_SECRET),
    )
    account_name = account_conf.get(CONF_ACCOUNT_NAME, CONST_PRIMARY)
    main_resource = account_conf.get(CONF_SHARED_MAILBOX)

    _LOGGER.debug("Permissions setup")
    perms = Permissions(hass, account_conf)
    permissions, failed_permissions = await perms.async_check_authorizations()
    account, is_authenticated = await _async_try_authentication(
        hass, perms, credentials, main_resource, account_name
    )

    if is_authenticated and permissions and permissions != TOKEN_FILE_MISSING:
        _LOGGER.debug("do setup")
        check_token = await _async_check_token(hass, account, account_name)
        if check_token:
            await do_setup(hass, account_conf, account, account_name, perms)
    else:
        await _async_authorization_repair(
            hass,
            account_conf,
            account,
            account_name,
            failed_permissions,
            permissions,
        )


async def _async_try_authentication(
    hass, perms, credentials, main_resource, account_name
):
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
    try:
        return account, account.is_authenticated

    except json.decoder.JSONDecodeError as err:
        _LOGGER.warning(
            "Token corrupt for account - please delete and re-authenticate: %s. Error - %s",
            account_name,
            err,
        )
        return account, False


async def _async_check_token(hass, account, account_name):
    try:
        await hass.async_add_executor_job(account.get_current_user)
        return True
    except InvalidClientError as err:
        if "client secret" in err.description and "expired" in err.description:
            _LOGGER.warning(
                "Client Secret expired for account: %s. Create new Client Secret in Azure App.",
                account_name,
            )
        else:
            _LOGGER.warning(
                "Token error for account: %s. Error - %s", account_name, err.description
            )
        return False


async def _async_authorization_repair(
    hass,
    account_conf,
    account,
    account_name,
    failed_permissions,
    token_missing,
):
    base_message = f"requesting authorization for account: {account_name}"
    message = (
        "No token file found;"
        if token_missing == TOKEN_FILE_MISSING
        else "Token doesn't have all required permissions;"
    )
    _LOGGER.warning("%s %s", message, base_message)
    data = {
        CONF_ACCOUNT_CONF: account_conf,
        CONF_ACCOUNT: account,
        CONF_ACCOUNT_NAME: account_name,
        CONF_FAILED_PERMISSIONS: failed_permissions,
    }
    # Register a repair issue
    async_create_issue(
        hass,
        DOMAIN,
        "authorization",
        data=data,
        is_fixable=True,
        # learn_more_url=url,
        severity=IssueSeverity.ERROR,
        translation_key="authorization",
        translation_placeholders={
            CONF_ACCOUNT_NAME: account_name,
        },
    )


class _IncreaseIndent(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(_IncreaseIndent, self).increase_indent(flow, False)
