"""Calendar constants."""

from enum import Enum

from homeassistant.const import Platform


class EventResponse(Enum):
    """Event response."""

    Accept = "accept"  # pylint: disable=invalid-name
    Tentative = "tentative"  # pylint: disable=invalid-name
    Decline = "decline"  # pylint: disable=invalid-name


PLATFORMS: list[Platform] = [Platform.CALENDAR]
DOMAIN = "ms365_calendar"

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

CALENDAR_ENTITY_ID_FORMAT = "calendar.{}"

CONF_BASIC_CALENDAR = "basic_calendar"
CONF_CAL_ID = "cal_id"
CONF_CALENDAR_LIST = "calendar_list"
CONF_DEVICE_ID = "device_id"
CONF_ENTITIES = "entities"
CONF_EXCLUDE = "exclude"
CONF_GROUPS = "groups"
CONF_HOURS_BACKWARD_TO_GET = "start_offset"
CONF_HOURS_FORWARD_TO_GET = "end_offset"
CONF_MAX_RESULTS = "max_results"
CONF_SEARCH = "search"
CONF_SENSITIVITY_EXCLUDE = "sensitivity_exclude"
CONF_TRACK = "track"
CONF_TRACK_NEW_CALENDAR = "track_new_calendar"

CONST_GROUP = "group:"

DAYS = {
    "MO": "monday",
    "TU": "tuesday",
    "WE": "wednesday",
    "TH": "thursday",
    "FR": "friday",
    "SA": "saturday",
    "SU": "sunday",
}

DEFAULT_OFFSET = "!!"

EVENT_CREATE_CALENDAR_EVENT = "create_calendar_event"
EVENT_MODIFY_CALENDAR_EVENT = "modify_calendar_event"
EVENT_MODIFY_CALENDAR_RECURRENCES = "modify_calendar_recurrences"
EVENT_REMOVE_CALENDAR_EVENT = "remove_calendar_event"
EVENT_REMOVE_CALENDAR_RECURRENCES = "remove_calendar_recurrences"
EVENT_RESPOND_CALENDAR_EVENT = "respond_calendar_event"

INDEXES = {
    "+1": "first",
    "+2": "second",
    "+3": "third",
    "+4": "fourth",
    "-1": "last",
}

PERM_CALENDARS_READ = "Calendars.Read"
PERM_CALENDARS_READBASIC = "Calendars.ReadBasic"
PERM_CALENDARS_READWRITE = "Calendars.ReadWrite"
PERM_GROUP_READ_ALL = "Group.Read.All"
PERM_GROUP_READWRITE_ALL = "Group.ReadWrite.All"

YAML_CALENDARS_FILENAME = "ms365_calendars{0}.yaml"
