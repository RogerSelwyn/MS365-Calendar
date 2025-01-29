"""Generic Permissions processes."""

import logging
import os
from copy import deepcopy

from O365 import FileSystemTokenBackend

from ..const import (
    CONF_ENTITY_NAME,
    MS365_STORAGE_TOKEN,
    TOKEN_ERROR_CORRUPT,
    TOKEN_ERROR_MISSING,
    TOKEN_ERROR_PERMISSIONS,
    TOKEN_FILE_CORRUPTED,
    TOKEN_FILE_PERMISSIONS,
    TOKEN_FILENAME,
)
from ..helpers.filemgmt import build_config_file_path
from ..integration.const_integration import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BasePermissions:
    """Class in support of building permission sets."""

    def __init__(self, hass, config):
        """Initialise the class."""
        self._hass = hass
        self._config = config

        self._requested_permissions = []
        self._permissions = []
        self.failed_permissions = []
        self.token_filename = self.build_token_filename()
        self.token_path = build_config_file_path(self._hass, MS365_STORAGE_TOKEN)
        _LOGGER.debug("Setup token")
        self.token_backend = FileSystemTokenBackend(
            token_path=self.token_path,
            token_filename=self.token_filename,
        )

    @property
    def requested_permissions(self):
        """Return the required scope."""

    @property
    def permissions(self):
        """Return the permission set."""
        return self._permissions

    async def async_check_authorizations(self):
        """Report on permissions status."""
        error, self._permissions = await self._hass.async_add_executor_job(
            self._get_permissions
        )

        if error in [TOKEN_FILE_CORRUPTED]:
            return error
        self.failed_permissions = []
        for permission in self.requested_permissions:
            if not self.validate_authorization(permission):
                self.failed_permissions.append(permission)

        if self.failed_permissions:
            _LOGGER.warning(
                TOKEN_ERROR_PERMISSIONS,
                ", ".join(self.failed_permissions),
                self.token_filename,
                self._config[CONF_ENTITY_NAME],
            )
            return TOKEN_FILE_PERMISSIONS

        return False

    def validate_authorization(self, permission):
        """Validate higher permissions."""
        if permission in self.permissions:
            return True

        if self._check_higher_permissions(permission):
            return True

        resource = permission.split(".")[0]
        constraint = (
            permission.split(".")[2] if len(permission.split(".")) == 3 else None
        )

        # If Calendar or Mail Resource then permissions can have a constraint of .Shared
        # which includes base as well. e.g. Calendars.Read is also enabled by Calendars.Read.Shared
        if not constraint and resource in ["Calendars", "Mail"]:
            sharedpermission = f"{deepcopy(permission)}.Shared"
            return self._check_higher_permissions(sharedpermission)
        # If Presence Resource then permissions can have a constraint of .All
        # which includes base as well. e.g. Presence.Read is also enabled by Presence.Read.All
        if not constraint and resource in ["Presence"]:
            allpermission = f"{deepcopy(permission)}.All"
            return self._check_higher_permissions(allpermission)

        return False

    def _check_higher_permissions(self, permission):
        operation = permission.split(".")[1]
        # If Operation is ReadBasic then Read or ReadWrite will also work
        # If Operation is Read then ReadWrite will also work
        newops = [operation]
        if operation == "ReadBasic":
            newops = newops + ["Read", "ReadWrite"]
        elif operation == "Read":
            newops = newops + ["ReadWrite"]

        for newop in newops:
            newperm = deepcopy(permission).replace(operation, newop)
            if newperm in self.permissions:
                return True

        return False

    def build_token_filename(self):
        """Create the token file name."""
        return TOKEN_FILENAME.format(DOMAIN, f"_{self._config.get(CONF_ENTITY_NAME)}")

    def _get_permissions(self):
        """Get the permissions from the token file."""

        scopes = self.token_backend.get_token_scopes()
        if scopes is None:
            _LOGGER.warning(
                TOKEN_ERROR_CORRUPT,
                DOMAIN,
                self._config[CONF_ENTITY_NAME],
                "No permissions",
            )
            return TOKEN_FILE_CORRUPTED, None

        for idx, scope in enumerate(scopes):
            scopes[idx] = scope.removeprefix("https://graph.microsoft.com/")

        return False, scopes

    def delete_token(self):
        """Delete the token."""
        full_token_path = os.path.join(self.token_path, self.token_filename)
        if os.path.exists(full_token_path):
            os.remove(full_token_path)

    def check_token_exists(self):
        """Check if token file exists.."""
        full_token_path = os.path.join(self.token_path, self.token_filename)
        if not os.path.exists(full_token_path) or not os.path.isfile(full_token_path):
            _LOGGER.warning(TOKEN_ERROR_MISSING, full_token_path)
            return False
        return True
