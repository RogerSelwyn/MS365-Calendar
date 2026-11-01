# pylint: disable=unused-import
"""Constants for calendar integration."""

from enum import Enum

from custom_components.ms365_calendar.config_flow import MS365ConfigFlow  # noqa: F401
from custom_components.ms365_calendar.const import (  # noqa: F401
    AUTH_CALLBACK_PATH_ALT,
    COUNTRY_URLS,
    OAUTH_REDIRECT_URL,
    CountryOptions,
)
from custom_components.ms365_calendar.integration.const_integration import DOMAIN  # noqa: F401

AUTH_CALLBACK_PATH_DEFAULT = COUNTRY_URLS[CountryOptions.DEFAULT][OAUTH_REDIRECT_URL]
BASE_CONFIG_ENTRY_INTEGRATION = {
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


MIGRATION_CONFIG_ENTRY = {
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
    """List of URLs."""

    OPENID = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
    ME = "https://graph.microsoft.com/v1.0/me"
    CALENDARS = "https://graph.microsoft.com/v1.0/me/calendars"
    GROUP_CALENDARS = "https://graph.microsoft.com/v1.0/groups"
    SHARED_CALENDARS = "https://graph.microsoft.com/v1.0/users/jane.doe@nomail.com/calendars"


class CN21VURL(Enum):
    """List of URLs."""

    DISCOVERY = "https://login.microsoftonline.com/common/discovery/instance"
    OPENID = "https://login.partner.microsoftonline.cn/common/v2.0/.well-known/openid-configuration"
    ME = "https://microsoftgraph.chinacloudapi.cn/v1.0/me"
    CALENDARS = "https://microsoftgraph.chinacloudapi.cn/v1.0/me/calendars"
    GROUP_CALENDARS = "https://microsoftgraph.chinacloudapi.cn/v1.0/groups"
