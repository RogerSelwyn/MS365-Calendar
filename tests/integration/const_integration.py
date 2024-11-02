# pylint: disable=unused-import
"""Constants for calendar integration."""

from copy import deepcopy
from enum import Enum

from custom_components.ms365_calendar.const import (  # noqa: F401
    AUTH_CALLBACK_PATH_ALT,
    AUTH_CALLBACK_PATH_DEFAULT,
)
from custom_components.ms365_calendar.integration.const_integration import (
    DOMAIN,  # noqa: F401
)

from ..const import CLIENT_ID, CLIENT_SECRET, ENTITY_NAME

BASE_CONFIG_ENTRY = {
    "entity_name": ENTITY_NAME,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "alt_auth_method": False,
    "enable_update": False,
    "basic_calendar": False,
    "groups": False,
    "shared_mailbox": "",
}
BASE_TOKEN_PERMS = "Calendars.Read"
UPDATE_TOKEN_PERMS = "Calendars.ReadWrite"

ALT_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
ALT_CONFIG_ENTRY["alt_auth_method"] = True

RECONFIGURE_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
del RECONFIGURE_CONFIG_ENTRY["entity_name"]


DIAGNOSTIC_GRANTED_PERMISSIONS = [
    "Calendars.Read",
    "User.Read",
    "profile",
    "openid",
    "email",
]
DIAGNOSTIC_REQUESTED_PERMISSIONS = [
    "offline_access",
    "User.Read",
    "Calendars.Read",
]

FULL_INIT_ENTITY_NO = 2

UPDATE_CALENDAR_LIST = ["Calendar1"]


class URL(Enum):
    """List of URLs"""

    ME = "https://graph.microsoft.com/v1.0/me"
    CALENDARS = "https://graph.microsoft.com/v1.0/me/calendars"
    GROUP_CALENDARS = "https://graph.microsoft.com/v1.0/groups"
    SHARED_CALENDARS = (
        "https://graph.microsoft.com/v1.0/users/jane.doe@nomail.com/calendars"
    )
