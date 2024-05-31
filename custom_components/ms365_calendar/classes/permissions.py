"""Permissions processes for calendar."""

import logging

from ..const import (
    CONF_ACCOUNT_NAME,
    CONF_SHARED_MAILBOX,
    PERM_OFFLINE_ACCESS,
    PERM_SHARED,
    PERM_USER_READ,
)
from ..const_calendar import (
    CONF_BASIC_CALENDAR,
    CONF_ENABLE_UPDATE,
    CONF_GROUPS,
    PERM_CALENDARS_READ,
    PERM_CALENDARS_READBASIC,
    PERM_CALENDARS_READWRITE,
    PERM_GROUP_READ_ALL,
    PERM_GROUP_READWRITE_ALL,
)
from .base_permissions import BasePermissions

_LOGGER = logging.getLogger(__name__)


class Permissions(BasePermissions):
    """Class in support of building permission sets."""

    def __init__(self, hass, config):
        """Initialise the class."""
        super().__init__(hass, config)

        self._shared = PERM_SHARED if config.get(CONF_SHARED_MAILBOX) else ""
        self._enable_update = self._config.get(CONF_ENABLE_UPDATE, False)

    @property
    def requested_permissions(self):
        """Return the required scope."""
        if not self._requested_permissions:
            self._requested_permissions = [PERM_OFFLINE_ACCESS, PERM_USER_READ]
            self._build_calendar_permissions()
            self._build_group_permissions()

        return self._requested_permissions

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
