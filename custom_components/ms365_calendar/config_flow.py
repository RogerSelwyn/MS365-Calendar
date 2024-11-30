"""Configuration flow for the skyq platform."""

import functools as ft
import json
import logging
from collections.abc import Mapping
from typing import Any, Self

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiohttp import web_response
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import (
    CONN_CLASS_CLOUD_POLL,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.network import get_url
from O365 import Account, FileSystemTokenBackend

from .const import (
    AUTH_CALLBACK_NAME,
    AUTH_CALLBACK_PATH_ALT,
    AUTH_CALLBACK_PATH_DEFAULT,
    CONF_ALT_AUTH_METHOD,
    CONF_AUTH_URL,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENTITY_NAME,
    CONF_FAILED_PERMISSIONS,
    CONF_SHARED_MAILBOX,
    CONF_URL,
    CONST_UTC_TIMEZONE,
    TOKEN_FILE_CORRUPTED,
    TOKEN_FILE_MISSING,
    TOKEN_FILE_PERMISSIONS,
)
from .helpers.config_entry import MS365ConfigEntry
from .integration.config_flow_integration import (
    MS365OptionsFlowHandler,
    async_integration_imports,
    integration_reconfigure_schema,
    integration_validate_schema,
)
from .integration.const_integration import DOMAIN
from .integration.permissions_integration import Permissions
from .integration.schema_integration import CONFIG_SCHEMA_INTEGRATION
from .schema import (
    CONFIG_SCHEMA,
    REQUEST_AUTHORIZATION_DEFAULT_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)


class MS365ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Example config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initiliase the configuration flow."""
        self._permissions = []
        self._failed_permissions = []
        self._account = None
        self._entity_name = None
        self._url = None
        self._callback_url = None
        self._state = None
        self._callback_view = None
        self._alt_auth_method = None
        self._user_input = None
        self._config_schema: dict[vol.Required, type[str | int]] | None = None
        self._reconfigure = False
        self._entry: MS365ConfigEntry | None = None
        # self._o365_config = None
        # self._ms365_config = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """MS365 options callback."""
        return MS365OptionsFlowHandler(config_entry)

    def is_matching(self, other_flow: Self) -> bool:
        """Return True if other_flow is matching this flow."""
        return other_flow.entity_name == self._entity_name

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # self._o365_config = self.hass.data.get("o365", None)
        # self._ms365_config = self.hass.config_entries.async_entries(DOMAIN)
        errors = integration_validate_schema(user_input) if user_input else {}

        if user_input and not errors:
            self._user_input = user_input

            if not self._entity_name:
                self._entity_name = user_input.get(CONF_ENTITY_NAME)
            else:
                user_input[CONF_ENTITY_NAME] = self._entity_name
            credentials = (
                user_input.get(CONF_CLIENT_ID),
                user_input.get(CONF_CLIENT_SECRET),
            )

            main_resource = user_input.get(CONF_SHARED_MAILBOX)
            self._alt_auth_method = user_input.get(CONF_ALT_AUTH_METHOD)
            self._permissions = Permissions(self.hass, user_input)
            self._permissions.token_filename = self._permissions.build_token_filename()
            (
                self._account,
                is_authenticated,
                auth_error,
            ) = await self.hass.async_add_executor_job(
                self._try_authentication,
                self._permissions,
                credentials,
                main_resource,
            )
            if not auth_error and (not is_authenticated or self._reconfigure):
                scope = self._permissions.requested_permissions
                self._callback_url = get_callback_url(self.hass, self._alt_auth_method)
                self._url, self._state = await self.hass.async_add_executor_job(
                    ft.partial(
                        self._account.con.get_authorization_url,
                        requested_scopes=scope,
                        redirect_uri=self._callback_url,
                    )
                )

                if self._alt_auth_method:
                    return await self.async_step_request_alt()

                return await self.async_step_request_default()

            if auth_error:
                errors[CONF_ENTITY_NAME] = "error_authenticating"
            else:
                errors[CONF_ENTITY_NAME] = "already_configured"

        data = self._config_schema or CONFIG_SCHEMA | CONFIG_SCHEMA_INTEGRATION
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data), errors=errors
        )

    async def async_step_request_default(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the confirm step of a fix flow."""
        errors = {}
        # _LOGGER.debug("Token file: %s", self._account.con.token_backend)
        if user_input is not None:
            errors = await self._async_validate_response(user_input)
            if not errors:
                return await self._async_create_update_entry()

        return self.async_show_form(
            step_id="request_default",
            data_schema=vol.Schema(REQUEST_AUTHORIZATION_DEFAULT_SCHEMA),
            description_placeholders={
                CONF_AUTH_URL: self._url,
                CONF_ENTITY_NAME: self._entity_name,
                CONF_FAILED_PERMISSIONS: self._failed_perms(),
            },
            errors=errors,
        )

    async def async_step_request_alt(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the confirm step of a fix flow."""
        errors = {}
        if user_input is not None:
            errors = await self._async_validate_response(user_input)
            if not errors:
                return await self._async_create_update_entry()

        if not self._callback_view:
            self._callback_view = MS365AuthCallbackView()
            self.hass.http.register_view(self._callback_view)

        return self.async_show_form(
            step_id="request_alt",
            description_placeholders={
                CONF_AUTH_URL: self._url,
                CONF_ENTITY_NAME: self._entity_name,
                CONF_FAILED_PERMISSIONS: self._failed_perms(),
            },
            errors=errors,
        )

    def _failed_perms(self):
        return (
            f"\n\nMissing - {', '.join(self._failed_permissions)}"
            if self._failed_permissions
            else None
        )

    async def _async_create_update_entry(self):
        if self._reconfigure:
            for error in [
                TOKEN_FILE_CORRUPTED,
                TOKEN_FILE_MISSING,
                TOKEN_FILE_PERMISSIONS,
            ]:
                ir.async_delete_issue(self.hass, DOMAIN, error)
            return self.async_update_reload_and_abort(
                self._entry, data_updates=self._user_input
            )

        return self.async_create_entry(title=self._entity_name, data=self._user_input)

    async def _async_validate_response(self, user_input):
        errors = {}
        url = (
            self._callback_view.token_url
            if self._alt_auth_method
            else user_input[CONF_URL]
        )
        if url[:5].lower() == "http:":
            url = f"https:{url[5:]}"
        if "code" not in url:
            errors[CONF_URL] = "invalid_url"
            return errors

        result = await self.hass.async_add_executor_job(
            ft.partial(
                self._account.con.request_token,
                url,
                state=self._state,
                redirect_uri=self._callback_url,
            )
        )

        if result is not True:
            _LOGGER.error("Token file error - check log for errors from O365")
            errors[CONF_URL] = "token_file_error"
            return errors

        (
            permissions,
            self._failed_permissions,
        ) = await self._permissions.async_check_authorizations()
        if permissions is not True:
            errors[CONF_URL] = permissions

        return errors

    def _try_authentication(self, perms, credentials, main_resource):
        _LOGGER.debug("Setup token")
        token_backend = FileSystemTokenBackend(
            token_path=perms.token_path,
            token_filename=perms.token_filename,
        )
        _LOGGER.debug("Setup account")
        account = Account(
            credentials,
            token_backend=token_backend,
            timezone=CONST_UTC_TIMEZONE,
            main_resource=main_resource,
        )
        try:
            return account, account.is_authenticated, False

        except json.decoder.JSONDecodeError as err:
            _LOGGER.error("Error authenticating - JSONDecodeError - %s", err)
            return account, False, err

    async def async_step_reconfigure(
        self,
        user_input: Mapping[str, Any] | None = None,  # pylint: disable=unused-argument
    ) -> ConfigFlowResult:
        """Trigger a reconfiguration flow."""
        self._entry = self._get_reconfigure_entry()
        assert self._entry
        return await self._redo_configuration(self._entry.data)

    async def _redo_configuration(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Re-run configuration step."""

        self._reconfigure = True
        self._entity_name = entry_data[CONF_ENTITY_NAME]
        self._config_schema = {
            vol.Required(CONF_CLIENT_ID, default=entry_data[CONF_CLIENT_ID]): vol.All(
                cv.string, vol.Strip
            ),
            vol.Required(
                CONF_CLIENT_SECRET, default=entry_data[CONF_CLIENT_SECRET]
            ): vol.All(cv.string, vol.Strip),
            vol.Optional(
                CONF_ALT_AUTH_METHOD, default=entry_data[CONF_ALT_AUTH_METHOD]
            ): cv.boolean,
        }
        self._config_schema |= integration_reconfigure_schema(entry_data)

        return await self.async_step_user()

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import a config entry."""
        data = import_data["data"]
        options = import_data["options"]
        self._entity_name = data[CONF_ENTITY_NAME]
        if self._check_existing():
            return self.async_abort(reason="already_configured")
        await async_integration_imports(self.hass, import_data)
        result = self.async_create_entry(
            title=self._entity_name, data=data, options=options
        )
        self._disable_new()
        return result

    def _check_existing(self):
        config_entries = self.hass.config_entries.async_entries(DOMAIN)
        for config_entry in config_entries:
            if config_entry.title == self._entity_name:
                return True
        return False

    def _disable_new(self):
        config_entries = self.hass.config_entries.async_entries(DOMAIN)
        for config_entry in config_entries:
            if config_entry.title == self._entity_name:
                config_entry.disabled_by = "migration"
                return


def get_callback_url(hass, alt_config):
    """Get the callback URL."""
    if alt_config:
        return f"{get_url(hass, prefer_external=True)}{AUTH_CALLBACK_PATH_ALT}"

    return AUTH_CALLBACK_PATH_DEFAULT


class MS365AuthCallbackView(HomeAssistantView):
    """MS365 Authorization Callback View."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH_ALT
    name = AUTH_CALLBACK_NAME

    def __init__(self):
        """Initialize."""
        self.token_url = None

    @callback
    async def get(self, request):
        """Receive authorization token."""
        self.token_url = str(request.url)

        return web_response.Response(
            headers={"content-type": "text/html"},
            text="<script>window.close()</script>This window can be closed",
        )
