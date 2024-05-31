"""Constants."""

from enum import Enum


class EventResponse(Enum):
    """Event response."""

    Accept = "accept"  # pylint: disable=invalid-name
    Tentative = "tentative"  # pylint: disable=invalid-name
    Decline = "decline"  # pylint: disable=invalid-name


ATTR_ALL_DAY = "all_day"
ATTR_ATTENDEES = "attendees"
ATTR_BODY = "body"
ATTR_CATEGORIES = "categories"
ATTR_COLOR = "color"
ATTR_DATA = "data"
ATTR_EMAIL = "email"
ATTR_END = "end"
ATTR_EVENT_ID = "event_id"
ATTR_HEX_COLOR = "hex_color"
ATTR_IS_ALL_DAY = "is_all_day"
ATTR_LOCATION = "location"
ATTR_MESSAGE = "message"
ATTR_OFFSET = "offset_reached"
ATTR_RESPONSE = "response"
ATTR_RRULE = "rrule"
ATTR_SEND_RESPONSE = "send_response"
ATTR_SENSITIVITY = "sensitivity"
ATTR_SHOW_AS = "show_as"
ATTR_START = "start"
ATTR_SUBJECT = "subject"
ATTR_TYPE = "type"
AUTH_CALLBACK_NAME = "api:ms365"
AUTH_CALLBACK_PATH_ALT = "/api/ms365"
AUTH_CALLBACK_PATH_DEFAULT = (
    "https://login.microsoftonline.com/common/oauth2/nativeclient"
)
CALENDAR_ENTITY_ID_FORMAT = "calendar.{}"
CONF_ACCOUNT_NAME = "account_name"
CONF_ALT_AUTH_METHOD = "alt_auth_method"
CONF_AUTH_URL = "auth_url"
CONF_BASIC_CALENDAR = "basic_calendar"
CONF_CAL_ID = "cal_id"
CONF_CALENDAR_LIST = "calendar_list"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"  # nosec
CONF_DEVICE_ID = "device_id"
CONF_ENABLE_UPDATE = "enable_update"
CONF_ENTITIES = "entities"
CONF_EXCLUDE = "exclude"
CONF_FAILED_PERMISSIONS = "failed_permissions"
CONF_GROUPS = "groups"
CONF_HOURS_BACKWARD_TO_GET = "start_offset"
CONF_HOURS_FORWARD_TO_GET = "end_offset"
CONF_MAX_RESULTS = "max_results"
CONF_SEARCH = "search"
CONF_SHARED_MAILBOX = "shared_mailbox"
CONF_TRACK = "track"
CONF_TRACK_NEW_CALENDAR = "track_new_calendar"
CONF_URL = "url"

CONST_GROUP = "group:"
CONST_UTC_TIMEZONE = "UTC"

DEFAULT_OFFSET = "!!"
DOMAIN = "ms365_calendar"

EVENT_HA_EVENT = "ha_event"

EVENT_CREATE_CALENDAR_EVENT = "create_calendar_event"
EVENT_MODIFY_CALENDAR_EVENT = "modify_calendar_event"
EVENT_MODIFY_CALENDAR_RECURRENCES = "modify_calendar_recurrences"
EVENT_REMOVE_CALENDAR_EVENT = "remove_calendar_event"
EVENT_REMOVE_CALENDAR_RECURRENCES = "remove_calendar_recurrences"
EVENT_RESPOND_CALENDAR_EVENT = "respond_calendar_event"

MS365_STORAGE = "ms365_storage"
MS365_STORAGE_TOKEN = ".MS365-token-cache"
PERM_CALENDARS_READ = "Calendars.Read"
PERM_CALENDARS_READBASIC = "Calendars.ReadBasic"
PERM_CALENDARS_READWRITE = "Calendars.ReadWrite"
PERM_GROUP_READ_ALL = "Group.Read.All"
PERM_GROUP_READWRITE_ALL = "Group.ReadWrite.All"
PERM_OFFLINE_ACCESS = "offline_access"
PERM_USER_READ = "User.Read"
PERM_SHARED = ".Shared"


TOKEN_FILENAME = "{0}{1}.token"  # nosec
TOKEN_FILE_MISSING = "missing"
YAML_CALENDARS_FILENAME = "ms365_calendars{0}.yaml"

DAYS = {
    "MO": "monday",
    "TU": "tuesday",
    "WE": "wednesday",
    "TH": "thursday",
    "FR": "friday",
    "SA": "saturday",
    "SU": "sunday",
}
INDEXES = {
    "+1": "first",
    "+2": "second",
    "+3": "third",
    "+4": "fourth",
    "-1": "last",
}
