"""Configuration flow for the skyq platform."""

import functools as ft
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
from homeassistant.data_entry_flow import FlowResult, section
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.network import get_url

from .classes.api import MS365Account, MS365Token
from .classes.config_entry import MS365ConfigEntry
from .const import (
    AUTH_CALLBACK_NAME,
    AUTH_CALLBACK_PATH_ALT,
    CONF_ALT_AUTH_METHOD,
    CONF_API_COUNTRY,
    CONF_API_OPTIONS,
    CONF_AUTH_URL,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_ENTITY_NAME,
    CONF_FAILED_PERMISSIONS,
    CONF_SHARED_MAILBOX,
    CONF_URL,
    COUNTRY_URLS,
    ERROR_IMPORTED_DUPLICATE,
    ERROR_INVALID_SHARED_MAILBOX,
    OAUTH_REDIRECT_URL,
    TOKEN_ERROR_FILE,
    TOKEN_FILE_CORRUPTED,
    TOKEN_FILE_EXPIRED,
    TOKEN_FILE_MISSING,
    TOKEN_FILE_PERMISSIONS,
    CountryOptions,
)
from .helpers.utils import get_country
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

    VERSION = 2
    MINOR_VERSION = 0
    CONNECTION_CLASS = CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialise the configuration flow."""
        self._permissions = []
        self._ms365account = None
        self._entity_name = None
        self._url = None
        self._flow = None
        self._callback_view = None
        self._user_input = None
        self._config_schema: dict[vol.Required, type[str | int]] | None = None
        self._reconfigure = False
        self._entry: MS365ConfigEntry | None = None

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
            alt_auth_method = self._user_input.get(CONF_ALT_AUTH_METHOD)
            token_backend = MS365Token(self.hass, user_input)
            self._permissions = Permissions(self.hass, user_input, token_backend)
            self._ms365account = MS365Account(self._permissions, user_input)
            auth_error = await self.hass.async_add_executor_job(
                self._ms365account.try_authentication,
                credentials,
                main_resource,
                self._entity_name,
            )
            if not auth_error and (
                not self._ms365account.is_authenticated or self._reconfigure
            ):
                scope = self._permissions.requested_permissions
                self._url, self._flow = await self.hass.async_add_executor_job(
                    ft.partial(
                        self._ms365account.account.get_authorization_url,
                        requested_scopes=scope,
                        redirect_uri=get_callback_url(
                            self.hass, alt_auth_method, user_input
                        ),
                    )
                )

                if alt_auth_method:
                    return await self.async_step_request_alt()

                return await self.async_step_request_default()

            attr_name = CONF_CLIENT_ID if self._reconfigure else CONF_ENTITY_NAME
            if auth_error:
                errors[attr_name] = "error_authenticating"
            else:
                errors[attr_name] = "already_configured"

        data = self._config_schema or CONFIG_SCHEMA | CONFIG_SCHEMA_INTEGRATION
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data), errors=errors
        )

    async def async_step_request_default(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the confirm step of a fix flow."""
        errors = {}
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
            f"\n\nMissing - {', '.join(self._permissions.failed_permissions)}"
            if self._permissions.failed_permissions
            else None
        )

    async def _async_create_update_entry(self):
        if self._reconfigure:
            for error in [
                TOKEN_FILE_CORRUPTED,
                TOKEN_FILE_MISSING,
                TOKEN_FILE_PERMISSIONS,
                TOKEN_FILE_EXPIRED,
            ]:
                ir.async_delete_issue(self.hass, DOMAIN, error)
            return self.async_update_reload_and_abort(
                self._entry, data=self._user_input
            )

        return self.async_create_entry(title=self._entity_name, data=self._user_input)

    async def _async_validate_response(self, user_input):
        errors = {}
        alt_auth_method = self._user_input.get(CONF_ALT_AUTH_METHOD)
        url = self._callback_view.token_url if alt_auth_method else user_input[CONF_URL]
        if url[:5].lower() == "http:":
            url = f"https:{url[5:]}"
        if "code" not in url:
            errors[CONF_URL] = "invalid_url"
            return errors

        if self._ms365account.account.username:
            await self.hass.async_add_executor_job(
                ft.partial(
                    self._ms365account.account.con.token_backend.remove_data,
                    username=self._ms365account.account.username,
                )
            )
        credentials = (
            self._user_input.get(CONF_CLIENT_ID),
            self._user_input.get(CONF_CLIENT_SECRET),
        )

        main_resource = self._user_input.get(CONF_SHARED_MAILBOX)

        result = await self.hass.async_add_executor_job(
            ft.partial(
                self._ms365account.account.request_token,
                url,
                flow=self._flow,
                redirect_uri=get_callback_url(
                    self.hass, alt_auth_method, self._user_input
                ),
            )
        )

        if result is not True:
            _LOGGER.error(TOKEN_ERROR_FILE)
            errors[CONF_URL] = "token_file_error"
            return errors

        (
            auth_error  # pylint: disable=unused-variable  # noqa: F841
        ) = await self.hass.async_add_executor_job(
            self._ms365account.try_authentication,
            credentials,
            main_resource,
            self._entity_name,
        )
        if (
            self._ms365account.account.username
            == self._ms365account.account.main_resource
        ):
            self._user_input[CONF_SHARED_MAILBOX] = None
            _LOGGER.warning(
                ERROR_INVALID_SHARED_MAILBOX, self._ms365account.account.username
            )

        error = await self._permissions.async_check_authorizations()
        if error:
            errors[CONF_URL] = error

        return errors

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
        country = get_country(entry_data)

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
            vol.Required(CONF_API_OPTIONS): section(
                vol.Schema(
                    {
                        vol.Required(
                            CONF_API_COUNTRY,
                            default=country,
                        ): vol.In(CountryOptions)
                    }
                ),
                {"collapsed": True},
            ),
        }
        self._config_schema |= integration_reconfigure_schema(entry_data)

        return await self.async_step_user()

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
        """Import a config entry."""
        data = import_data["data"]
        options = import_data["options"]
        self._entity_name = data[CONF_ENTITY_NAME]
        if self._check_existing():
            _LOGGER.info(ERROR_IMPORTED_DUPLICATE, DOMAIN, self._entity_name)
            return self.async_abort(reason="already_configured")
        await async_integration_imports(self.hass, import_data)
        return self.async_create_entry(
            title=self._entity_name, data=data, options=options
        )

    def _check_existing(self):
        config_entries = self.hass.config_entries.async_entries(DOMAIN)
        return any(
            config_entry.title == self._entity_name for config_entry in config_entries
        )


def get_callback_url(hass, alt_config, user_input):
    """Get the callback URL."""
    if alt_config:
        return f"{get_url(hass, prefer_external=True)}{AUTH_CALLBACK_PATH_ALT}"

    country = user_input[CONF_API_OPTIONS][CONF_API_COUNTRY]
    return COUNTRY_URLS[country][OAUTH_REDIRECT_URL]


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
