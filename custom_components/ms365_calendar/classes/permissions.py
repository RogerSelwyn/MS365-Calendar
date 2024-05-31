"""Permissions processes."""

import json
import logging
import os
from copy import deepcopy

from ..const import (
    CONF_ACCOUNT_NAME,
    CONF_BASIC_CALENDAR,
    CONF_ENABLE_UPDATE,
    CONF_GROUPS,
    CONF_SHARED_MAILBOX,
    DOMAIN,
    MS365_STORAGE_TOKEN,
    PERM_CALENDARS_READ,
    PERM_CALENDARS_READBASIC,
    PERM_CALENDARS_READWRITE,
    PERM_GROUP_READ_ALL,
    PERM_GROUP_READWRITE_ALL,
    PERM_OFFLINE_ACCESS,
    PERM_SHARED,
    PERM_USER_READ,
    TOKEN_FILE_MISSING,
    TOKEN_FILENAME,
)
from ..helpers.filemgmt import build_config_file_path

_LOGGER = logging.getLogger(__name__)


class Permissions:
    """Class in support of building permssion sets."""

    def __init__(self, hass, config):
        """Initialise the class."""
        self._hass = hass
        self._config = config

        self._shared = PERM_SHARED if config.get(CONF_SHARED_MAILBOX) else ""
        self._enable_update = self._config.get(CONF_ENABLE_UPDATE, False)
        self._requested_permissions = []
        self.token_filename = self._build_token_filename()
        self.token_path = build_config_file_path(self._hass, MS365_STORAGE_TOKEN)
        self._permissions = []

    @property
    def requested_permissions(self):
        """Return the required scope."""
        if not self._requested_permissions:
            self._requested_permissions = [PERM_OFFLINE_ACCESS, PERM_USER_READ]
            self._build_calendar_permissions()
            self._build_group_permissions()

        return self._requested_permissions

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
                self._config[CONF_ACCOUNT_NAME],
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

    def _build_token_filename(self):
        """Create the token file name."""
        return TOKEN_FILENAME.format(DOMAIN, f"_{self._config.get(CONF_ACCOUNT_NAME)}")

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

    def _build_calendar_permissions(self):
        if self._config.get(CONF_BASIC_CALENDAR, False):
            if self._enable_update:
                _LOGGER.warning(
                    "'enable_update' should not be true when 'basic_calendar' is true ."
                    + "for account: %s ReadBasic used. ",
                    self._config[CONF_ACCOUNT_NAME],
                )
            self._requested_permissions.append(PERM_CALENDARS_READBASIC + self._shared)
        elif self._enable_update:
            self._requested_permissions.append(PERM_CALENDARS_READWRITE + self._shared)

        else:
            self._requested_permissions.append(PERM_CALENDARS_READ + self._shared)

    def _build_group_permissions(self):
        if self._config.get(CONF_GROUPS, False):
            if self._enable_update:
                self._requested_permissions.append(PERM_GROUP_READWRITE_ALL)
            else:
                self._requested_permissions.append(PERM_GROUP_READ_ALL)
