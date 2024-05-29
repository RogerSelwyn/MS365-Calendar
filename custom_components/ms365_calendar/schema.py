"""Schema for O365 Integration."""

import datetime
from collections.abc import Callable
from itertools import groupby
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.util import dt as dt_util
from O365.calendar import (  # pylint: disable=no-name-in-module
    AttendeeType,
    EventSensitivity,
    EventShowAs,
)

from .const import (
    ATTR_ATTENDEES,
    ATTR_BODY,
    ATTR_CATEGORIES,
    ATTR_EMAIL,
    ATTR_END,
    ATTR_EVENT_ID,
    ATTR_IS_ALL_DAY,
    ATTR_LOCATION,
    ATTR_MESSAGE,
    ATTR_RESPONSE,
    ATTR_SEND_RESPONSE,
    ATTR_SENSITIVITY,
    ATTR_SHOW_AS,
    ATTR_START,
    ATTR_SUBJECT,
    ATTR_TYPE,
    CONF_ACCOUNT_NAME,
    CONF_ACCOUNTS,
    CONF_ALT_AUTH_METHOD,
    CONF_BASIC_CALENDAR,
    CONF_CAL_ID,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_ENABLE_UPDATE,
    CONF_ENTITIES,
    CONF_EXCLUDE,
    CONF_GROUPS,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_SEARCH,
    CONF_SHARED_MAILBOX,
    CONF_TRACK,
    CONF_TRACK_NEW_CALENDAR,
    CONF_URL,
    EventResponse,
)


def _has_consistent_timezone(*keys: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Verify that all datetime values have a consistent timezone."""

    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        """Test that all keys that are datetime values have the same timezone."""
        tzinfos = []
        for key in keys:
            if not (value := obj.get(key)) or not isinstance(value, datetime.datetime):
                return obj
            tzinfos.append(value.tzinfo)
        uniq_values = groupby(tzinfos)
        if len(list(uniq_values)) > 1:
            raise vol.Invalid("Expected all values to have the same timezone")
        return obj

    return validate


def _as_local_timezone(*keys: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Convert all datetime values to the local timezone."""

    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        """Convert all keys that are datetime values to local timezone."""
        for k in keys:
            if (value := obj.get(k)) and isinstance(value, datetime.datetime):
                obj[k] = dt_util.as_local(value)
        return obj

    return validate


MULTI_ACCOUNT_SCHEMA = vol.Schema(
    {
        CONF_ACCOUNTS: vol.Schema(
            [
                {
                    vol.Required(CONF_CLIENT_ID): cv.string,
                    vol.Required(CONF_CLIENT_SECRET): cv.string,
                    vol.Optional(CONF_TRACK_NEW_CALENDAR, default=True): bool,
                    vol.Optional(CONF_ENABLE_UPDATE, default=False): bool,
                    vol.Optional(CONF_GROUPS, default=False): bool,
                    vol.Required(CONF_ACCOUNT_NAME, ""): cv.string,
                    vol.Optional(CONF_ALT_AUTH_METHOD, default=False): bool,
                    vol.Optional(CONF_BASIC_CALENDAR, default=False): bool,
                    vol.Optional(CONF_SHARED_MAILBOX, None): cv.string,
                }
            ]
        )
    }
)

CALENDAR_SERVICE_RESPOND_SCHEMA = {
    vol.Required(ATTR_EVENT_ID): cv.string,
    vol.Required(ATTR_RESPONSE, None): cv.enum(EventResponse),
    vol.Optional(ATTR_SEND_RESPONSE, True): bool,
    vol.Optional(ATTR_MESSAGE, None): cv.string,
}

CALENDAR_SERVICE_ATTENDEE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_EMAIL): cv.string,
        vol.Required(ATTR_TYPE): cv.enum(AttendeeType),
    }
)

CALENDAR_SERVICE_CREATE_SCHEMA = vol.All(
    cv.make_entity_service_schema(
        {
            vol.Required(ATTR_SUBJECT): cv.string,
            vol.Required(ATTR_START): cv.datetime,
            vol.Required(ATTR_END): cv.datetime,
            vol.Optional(ATTR_BODY): cv.string,
            vol.Optional(ATTR_LOCATION): cv.string,
            vol.Optional(ATTR_CATEGORIES): [cv.string],
            vol.Optional(ATTR_SENSITIVITY): vol.Coerce(EventSensitivity),
            vol.Optional(ATTR_SHOW_AS): vol.Coerce(EventShowAs),
            vol.Optional(ATTR_IS_ALL_DAY): bool,
            vol.Optional(ATTR_ATTENDEES): [CALENDAR_SERVICE_ATTENDEE_SCHEMA],
        }
    ),
    _has_consistent_timezone(ATTR_START, ATTR_END),
    _as_local_timezone(ATTR_START, ATTR_END),
)

CALENDAR_SERVICE_MODIFY_SCHEMA = vol.All(
    cv.make_entity_service_schema(
        {
            vol.Required(ATTR_EVENT_ID): cv.string,
            vol.Optional(ATTR_START): cv.datetime,
            vol.Optional(ATTR_END): cv.datetime,
            vol.Optional(ATTR_SUBJECT): cv.string,
            vol.Optional(ATTR_BODY): cv.string,
            vol.Optional(ATTR_LOCATION): cv.string,
            vol.Optional(ATTR_CATEGORIES): [cv.string],
            vol.Optional(ATTR_SENSITIVITY): vol.Coerce(EventSensitivity),
            vol.Optional(ATTR_SHOW_AS): vol.Coerce(EventShowAs),
            vol.Optional(ATTR_IS_ALL_DAY): bool,
            vol.Optional(ATTR_ATTENDEES): [CALENDAR_SERVICE_ATTENDEE_SCHEMA],
        }
    ),
    _has_consistent_timezone(ATTR_START, ATTR_END),
    _as_local_timezone(ATTR_START, ATTR_END),
)


CALENDAR_SERVICE_REMOVE_SCHEMA = {
    vol.Required(ATTR_EVENT_ID): cv.string,
}

YAML_CALENDAR_ENTITY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_HOURS_FORWARD_TO_GET, default=24): int,
        vol.Optional(CONF_HOURS_BACKWARD_TO_GET, default=0): int,
        vol.Optional(CONF_SEARCH): cv.string,
        vol.Optional(CONF_EXCLUDE): [cv.string],
        vol.Optional(CONF_TRACK): cv.boolean,
        vol.Optional(CONF_MAX_RESULTS): cv.positive_int,
    }
)

YAML_CALENDAR_DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CAL_ID): cv.string,
        vol.Required(CONF_ENTITIES, None): vol.All(
            cv.ensure_list, [YAML_CALENDAR_ENTITY_SCHEMA]
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

REQUEST_AUTHORIZATION_DEFAULT_SCHEMA = {vol.Required(CONF_URL): cv.string}
