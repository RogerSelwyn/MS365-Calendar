"""Generic Permissions processes."""

import json
import logging
import os
from copy import deepcopy

from ..const import (
    CONF_ENTITY_NAME,
    MS365_STORAGE_TOKEN,
    PERM_OFFLINE_ACCESS,
    TOKEN_FILE_MISSING,
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
        self.token_filename = self.build_token_filename()
        self.token_path = build_config_file_path(self._hass, MS365_STORAGE_TOKEN)
        self._permissions = []

    @property
    def requested_permissions(self):
        """Return the required scope."""

    @property
    def permissions(self):
        """Return the permission set."""
        return self._permissions

    async def async_check_authorizations(self):
        """Report on permissions status."""
        self._permissions = await self._hass.async_add_executor_job(
            self._get_permissions
        )

        if self.permissions == TOKEN_FILE_MISSING:
            return TOKEN_FILE_MISSING, None
        failed_permissions = []
        for permission in self.requested_permissions:
            if permission == PERM_OFFLINE_ACCESS:
                continue
            if not self.validate_authorization(permission):
                failed_permissions.append(permission)

        if failed_permissions:
            _LOGGER.warning(
                "Minimum required permissions: '%s'. Not available in token '%s' for account '%s'.",
                ", ".join(failed_permissions),
                self.token_filename,
                self._config[CONF_ENTITY_NAME],
            )
            return False, failed_permissions

        return True, None

    def validate_authorization(self, permission):
        """Validate higher permissions."""
        if permission in self.permissions:
            return True

        if self._check_higher_permissions(permission):
            return True

        resource = permission.split(".")[0]
        constraint = permission.split(".")[1] if len(permission) == 3 else None

        # If Calendar or Mail Resource then permissions can have a constraint of .Shared
        # which includes base as well. e.g. Calendar.Read is also enabled by Calendar.Read.Shared
        if not constraint and resource in ["Calendar", "Mail"]:
            sharedpermission = f"{deepcopy(permission)}.Shared"
            return self._check_higher_permissions(sharedpermission)
        # If Presence Resource then permissions can have a constraint of .All
        # which includes base as well. e.g. Presencedar.Read is also enabled by Presence.Read.All
        if not constraint and resource in ["Presence"]:
            allpermission = f"{deepcopy(permission)}.All"
            return self._check_higher_permissions(allpermission)

        return False

    def _check_higher_permissions(self, permission):
        operation = permission.split(".")[1]
        # If Operation is Send there are no alternatives
        # If Operation is ReadBasic then Read or ReadWrite will also work
        # If Operation is Read then ReadWrite will also work
        if operation == "Send":
            newops = []
        elif operation == "ReadBasic":
            newops = ["Read", "ReadWrite"]
        else:
            newops = ["ReadWrite"]
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
        full_token_path = os.path.join(self.token_path, self.token_filename)
        if not os.path.exists(full_token_path) or not os.path.isfile(full_token_path):
            _LOGGER.warning("Could not locate token at %s", full_token_path)
            return TOKEN_FILE_MISSING
        with open(full_token_path, "r", encoding="UTF-8") as file_handle:
            raw = file_handle.read()
            permissions = json.loads(raw)["scope"]

        return permissions
