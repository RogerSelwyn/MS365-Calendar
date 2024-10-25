"""Constants for MS365 testing."""

from enum import Enum

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
TITLE = "mock"
ENTITY_NAME = "test"

# AUTH_URL = "https://its_a_fake_url"
# TOKEN_URL = "http://its_another_fake_url_with_a_code=12345"
TOKEN_PARAMS = "code=fake.code&state={0}&session_state=fakesessionstate"
TOKEN_URL_ASSERT = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/"
    + "authorize?response_type=code&client_id="
)

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


UPDATE_CALENDAR_LIST = ["Calendar1"]


class URL(Enum):
    """List of URLs"""

    ME = "https://graph.microsoft.com/v1.0/me"
    CALENDARS = "https://graph.microsoft.com/v1.0/me/calendars"
    GROUP_CALENDARS = "https://graph.microsoft.com/v1.0/groups"
    SHARED_CALENDARS = (
        "https://graph.microsoft.com/v1.0/users/jane.doe@nomail.com/calendars"
    )
