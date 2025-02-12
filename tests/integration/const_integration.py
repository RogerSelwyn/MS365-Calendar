# pylint: disable=unused-import
"""Constants for calendar integration."""

from copy import deepcopy
from enum import Enum

from custom_components.ms365_calendar.config_flow import MS365ConfigFlow  # noqa: F401
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
BASE_MISSING_PERMS = BASE_TOKEN_PERMS
SHARED_TOKEN_PERMS = "Calendars.Read.Shared"
UPDATE_TOKEN_PERMS = "Calendars.ReadWrite"
UPDATE_OPTIONS = {"enable_update": True}

ALT_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
ALT_CONFIG_ENTRY["alt_auth_method"] = True

RECONFIGURE_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
del RECONFIGURE_CONFIG_ENTRY["entity_name"]

MIGRATION_CONFIG_ENTRY = {
    "data": BASE_CONFIG_ENTRY,
    "options": {},
    "calendars": {
        "calendar1": {
            "cal_id": "calendar1",
            "entities": [
                {
                    "device_id": "Calendar",
                    "end_offset": 6,
                    "name": "Calendar",
                    "start_offset": 0,
                    "track": False,
                }
            ],
        },
    },
}


DIAGNOSTIC_GRANTED_PERMISSIONS = [
    "Calendars.Read",
    "User.Read",
    "email",
    "openid",
    "profile",
]
DIAGNOSTIC_REQUESTED_PERMISSIONS = [
    "User.Read",
    "Calendars.Read",
]

FULL_INIT_ENTITY_NO = 3

UPDATE_CALENDAR_LIST = ["Calendar1"]


class URL(Enum):
    """List of URLs"""

    OPENID = (
        "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
    )
    ME = "https://graph.microsoft.com/v1.0/me"
    CALENDARS = "https://graph.microsoft.com/v1.0/me/calendars"
    GROUP_CALENDARS = "https://graph.microsoft.com/v1.0/groups"
    SHARED_CALENDARS = (
        "https://graph.microsoft.com/v1.0/users/jane.doe@nomail.com/calendars"
    )
