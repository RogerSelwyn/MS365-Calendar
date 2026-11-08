"""Schema for MS365 Integration."""

from collections.abc import Callable
import datetime as dt
from itertools import groupby
from typing import Any

import probatio

from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import BooleanSelector
from homeassistant.util import dt as dt_util
from O365.calendar import AttendeeType, EventSensitivity, EventShowAs  # pylint: disable=no-name-in-module

from ..const import CONF_ENABLE_UPDATE, CONF_SHARED_MAILBOX
from .const_integration import (
    ATTR_ATTENDEES,
    ATTR_BODY,
    ATTR_CATEGORIES,
    ATTR_EMAIL,
    ATTR_END,
    ATTR_END_DATE_TIME,
    ATTR_EVENT_ID,
    ATTR_IS_ALL_DAY,
    ATTR_IS_REMINDER_ON,
    ATTR_LOCATION,
    ATTR_MESSAGE,
    ATTR_REMIND_BEFORE_MINUTES,
    ATTR_RESPONSE,
    ATTR_SEND_RESPONSE,
    ATTR_SENSITIVITY,
    ATTR_SHOW_AS,
    ATTR_START,
    ATTR_START_DATE_TIME,
    ATTR_SUBJECT,
    ATTR_TYPE,
    CONF_BASIC_CALENDAR,
    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_ENTITIES,
    CONF_EXCLUDE,
    CONF_GROUPS,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_SEARCH,
    CONF_SENSITIVITY_EXCLUDE,
    CONF_TRACK,
    DEFAULT_HOURS_BACKWARD_TO_GET,
    DEFAULT_HOURS_FORWARD_TO_GET,
    EventResponse,
)


def _has_consistent_timezone(*keys: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Verify that all datetime values have a consistent timezone."""

    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        """Test that all keys that are datetime values have the same timezone."""
        tzinfos = []
        for key in keys:
            if obj.get(key):
                tzinfos.append(obj.get(key).tzinfo)  # noqa: PERF401
        uniq_values = groupby(tzinfos)
        if len(list(uniq_values)) > 1:
            raise probatio.Invalid("Expected all values to have the same timezone")
        return obj

    return validate


def _as_local_timezone(*keys: Any) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Convert all datetime values to the local timezone."""

    def validate(obj: dict[str, Any]) -> dict[str, Any]:
        """Convert all keys that are datetime values to local timezone."""
        for k in keys:
            if (value := obj.get(k)) and isinstance(value, dt.datetime):
                obj[k] = dt_util.as_local(value)
        return obj

    return validate


CONFIG_SCHEMA_INTEGRATION = {
    probatio.Optional(CONF_ENABLE_UPDATE, default=False): BooleanSelector(),
    probatio.Optional(CONF_BASIC_CALENDAR, default=False): BooleanSelector(),
    probatio.Optional(CONF_GROUPS, default=False): BooleanSelector(),
    probatio.Optional(CONF_SHARED_MAILBOX, default=""): cv.string,
}

CALENDAR_SERVICE_RESPOND_SCHEMA = {
    probatio.Required(ATTR_EVENT_ID): cv.string,
    probatio.Required(ATTR_RESPONSE, None): cv.enum(EventResponse),
    probatio.Optional(ATTR_SEND_RESPONSE, True): bool,
    probatio.Optional(ATTR_MESSAGE, None): cv.string,
}

CALENDAR_SERVICE_ATTENDEE_SCHEMA = probatio.Schema(
    {
        probatio.Required(ATTR_EMAIL): cv.string,
        probatio.Required(ATTR_TYPE): cv.enum(AttendeeType),
    }
)

CALENDAR_SERVICE_CREATE_SCHEMA = probatio.All(
    cv.make_entity_service_schema(
        {
            probatio.Required(ATTR_SUBJECT): cv.string,
            probatio.Required(ATTR_START): cv.datetime,
            probatio.Required(ATTR_END): cv.datetime,
            probatio.Optional(ATTR_BODY): cv.string,
            probatio.Optional(ATTR_LOCATION): cv.string,
            probatio.Optional(ATTR_CATEGORIES, default=list): probatio.All(
                cv.ensure_list, [cv.string]
            ),
            probatio.Optional(ATTR_SENSITIVITY): probatio.Coerce(EventSensitivity),
            probatio.Optional(ATTR_SHOW_AS): probatio.Coerce(EventShowAs),
            probatio.Optional(ATTR_IS_ALL_DAY): bool,
            probatio.Optional(ATTR_ATTENDEES): [CALENDAR_SERVICE_ATTENDEE_SCHEMA],
            probatio.Optional(ATTR_IS_REMINDER_ON): bool,
            probatio.Optional(ATTR_REMIND_BEFORE_MINUTES): probatio.All(
                probatio.Coerce(int), probatio.Range(min=0, max=1440)
            ),
        }
    ),
    _has_consistent_timezone(ATTR_START, ATTR_END),
    _as_local_timezone(ATTR_START, ATTR_END),
)

CALENDAR_SERVICE_MODIFY_SCHEMA = probatio.All(
    cv.make_entity_service_schema(
        {
            probatio.Required(ATTR_EVENT_ID): cv.string,
            probatio.Optional(ATTR_START): cv.datetime,
            probatio.Optional(ATTR_END): cv.datetime,
            probatio.Optional(ATTR_SUBJECT): cv.string,
            probatio.Optional(ATTR_BODY): cv.string,
            probatio.Optional(ATTR_LOCATION): cv.string,
            probatio.Optional(ATTR_CATEGORIES): probatio.All(
                cv.ensure_list, [cv.string]
            ),
            probatio.Optional(ATTR_SENSITIVITY): probatio.Coerce(EventSensitivity),
            probatio.Optional(ATTR_SHOW_AS): probatio.Coerce(EventShowAs),
            probatio.Optional(ATTR_IS_ALL_DAY): bool,
            probatio.Optional(ATTR_ATTENDEES): [CALENDAR_SERVICE_ATTENDEE_SCHEMA],
            probatio.Optional(ATTR_IS_REMINDER_ON): bool,
            probatio.Optional(ATTR_REMIND_BEFORE_MINUTES): probatio.All(
                probatio.Coerce(int), probatio.Range(min=0, max=1440)
            ),
        }
    ),
    _has_consistent_timezone(ATTR_START, ATTR_END),
    _as_local_timezone(ATTR_START, ATTR_END),
)


CALENDAR_SERVICE_REMOVE_SCHEMA = {
    probatio.Required(ATTR_EVENT_ID): cv.string,
}

CALENDAR_SERVICE_GET_EVENTS_SCHEMA = {
    probatio.Required(ATTR_START_DATE_TIME): cv.datetime,
    probatio.Required(ATTR_END_DATE_TIME): cv.datetime,
}

YAML_CALENDAR_ENTITY_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_NAME): cv.string,
        probatio.Required(CONF_DEVICE_ID): cv.string,
        probatio.Optional(
            CONF_HOURS_FORWARD_TO_GET, default=DEFAULT_HOURS_FORWARD_TO_GET
        ): int,
        probatio.Optional(
            CONF_HOURS_BACKWARD_TO_GET, default=DEFAULT_HOURS_BACKWARD_TO_GET
        ): int,
        probatio.Required(CONF_TRACK): cv.boolean,
        probatio.Optional(CONF_SEARCH): cv.string,
        probatio.Optional(CONF_EXCLUDE): [cv.string],
        probatio.Optional(CONF_MAX_RESULTS): cv.positive_int,
        probatio.Optional(CONF_SENSITIVITY_EXCLUDE): probatio.All(
            cv.ensure_list, [probatio.Coerce(EventSensitivity)]
        ),
    }
)

YAML_CALENDAR_DEVICE_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_CAL_ID): cv.string,
        probatio.Required(CONF_ENTITIES, None): probatio.All(
            cv.ensure_list, [YAML_CALENDAR_ENTITY_SCHEMA]
        ),
    },
    extra=probatio.ALLOW_EXTRA,
)
