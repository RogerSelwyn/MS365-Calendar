"""Calendar utilities processes."""

from datetime import datetime, time
import logging
import warnings
from zoneinfo import ZoneInfoNotFoundError

from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from dateutil import parser

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util, slugify
from O365.calendar import Attendee  # pylint: disable=no-name-in-module)
from O365.utils.windows_tz import (  # pylint: disable=no-name-in-module, import-error
    get_windows_tz,
)

from ..classes.config_entry import MS365ConfigEntry
from ..const import CONF_ENTITY_NAME
from .const_integration import (
    ATTR_ATTENDEES,
    ATTR_BODY,
    ATTR_BODY_IS_TEXT,
    ATTR_CATEGORIES,
    ATTR_IS_ALL_DAY,
    ATTR_IS_REMINDER_ON,
    ATTR_LOCATION,
    ATTR_REMIND_BEFORE_MINUTES,
    ATTR_RRULE,
    ATTR_SENSITIVITY,
    ATTR_SHOW_AS,
    CALENDAR_ENTITY_ID_FORMAT,
    DAYS,
    INDEXES,
)

_LOGGER = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)


def clean_html(html):
    """Clean the HTML."""
    soup = BeautifulSoup(html, features="html.parser")
    if body := soup.find("body"):
        # get text
        text = body.get_text()

        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)
        return text.replace("\xa0", " ")

    return html


def format_event_data(event):
    """Format the event data."""
    attendees = event.attendees._Attendees__attendees  # noqa: SLF001
    return {
        "summary": event.subject,
        "start": get_hass_date(event.start, event.is_all_day),
        "end": get_hass_date(get_end_date(event), event.is_all_day),
        "all_day": event.is_all_day,
        "description": clean_html(event.body),
        "location": event.location["displayName"],
        "categories": event.categories,
        "sensitivity": event.sensitivity.name,
        "show_as": event.show_as.name,
        "reminder": {
            "minutes": event.remind_before_minutes,
            "is_on": event.is_reminder_on,
        },
        "organizer": event.organizer.address,
        "attendees": [
            {
                "email": x.address,
                "type": x.attendee_type.value,
                "status": x.response_status.status.value
                if x.response_status.status
                else None,
            }
            for x in attendees
        ],
        "uid": event.object_id,
    }


def get_hass_date(obj, is_all_day):
    """Get the date."""
    return obj if isinstance(obj, datetime) and not is_all_day else obj.date()


def get_end_date(obj):
    """Get the end date."""
    return obj.end


def get_start_date(obj):
    """Get the start date."""
    return obj.start


def add_call_data_to_event(event, subject, start, end, **kwargs):
    """Add the call data.

    Only what is supplied is set. O365 sends every attribute that has been set, even
    to its current value, so anything else is left out of an update.
    """
    is_all_day = _is_all_day(kwargs.get(ATTR_IS_ALL_DAY), event, start, end)
    _add_attribute(event, "subject", subject)
    _add_body(kwargs.get(ATTR_BODY), kwargs.get(ATTR_BODY_IS_TEXT, False), event)
    _add_attribute(event, "location", kwargs.get(ATTR_LOCATION))
    _add_attribute(event, "categories", kwargs.get(ATTR_CATEGORIES))
    _add_attribute(event, "show_as", kwargs.get(ATTR_SHOW_AS))
    _add_attribute(event, "start", start)
    _add_attribute(event, "end", end)
    _add_attribute(event, "is_reminder_on", kwargs.get(ATTR_IS_REMINDER_ON))
    if event.is_reminder_on:
        _add_attribute(
            event, "remind_before_minutes", kwargs.get(ATTR_REMIND_BEFORE_MINUTES)
        )
    _add_attribute(event, "sensitivity", kwargs.get(ATTR_SENSITIVITY))
    _add_attendees(kwargs.get(ATTR_ATTENDEES, []), event)
    _add_all_day(is_all_day, event)

    if kwargs.get(ATTR_RRULE):
        _rrule_processing(event, kwargs[ATTR_RRULE])
    return event


def is_unchanged_text(text, body):
    """Check if text from the HA calendar is just the text of the body."""
    return text is not None and text.strip() == clean_html(body).strip()


def _add_attribute(event, name, value):
    if value is not None:
        setattr(event, name, value)


def _add_body(body, body_is_text, event):
    if body is None:
        return
    if body_is_text:
        # The HA calendar only has the text from clean_html, so writing it back
        # unchanged would replace the HTML body and lose its links and formatting
        if is_unchanged_text(body, event.body):
            return
        event.body_type = "text"
    event.body = body


def _is_all_day(is_all_day, event, start, end):
    """Work out the all day setting when the caller did not give one."""
    if is_all_day is not None or not event.is_all_day:
        return is_all_day
    # Times of day on an all day event mean it is moving to a timed slot
    for value in (start, end):
        if isinstance(value, datetime) and dt_util.as_local(value).time() != time():
            return False
    return None


def _add_attendees(attendees, event):
    if attendees:
        event.attendees.clear()
        event.attendees.add(
            [
                Attendee(x["email"], attendee_type=x["type"], event=event)
                for x in attendees
            ]
        )


def _add_all_day(is_all_day, event):
    if is_all_day is not None:
        event.is_all_day = is_all_day
        if event.is_all_day:
            event.start = datetime(
                event.start.year,
                event.start.month,
                event.start.day,
                0,
                0,
                0,
                tzinfo=dt_util.DEFAULT_TIME_ZONE,
            )
            event.end = datetime(
                event.end.year,
                event.end.month,
                event.end.day,
                0,
                0,
                0,
                tzinfo=dt_util.DEFAULT_TIME_ZONE,
            )


def _rrule_processing(event, rrule):
    rules = {}
    for item in rrule.split(";"):
        keys = item.split("=")
        rules[keys[0]] = keys[1]

    # Without a start date, O365 starts the series today rather than on the event
    kwargs = {"start": _local_date(event.start, event.is_all_day)}
    if "COUNT" in rules:
        kwargs["occurrences"] = int(rules["COUNT"])
    if "UNTIL" in rules:
        kwargs["end"] = _local_date(parser.parse(rules["UNTIL"]), False)
    interval = int(rules["INTERVAL"]) if "INTERVAL" in rules else 1
    if "BYDAY" in rules:
        days, index = _process_byday(rules["BYDAY"])
        kwargs["days_of_week"] = days
        if index:
            kwargs["index"] = index

    if rules["FREQ"] == "YEARLY":
        kwargs["day_of_month"] = event.start.day
        event.recurrence.set_yearly(interval, event.start.month, **kwargs)

    if rules["FREQ"] == "MONTHLY":
        if "BYDAY" not in rules:
            kwargs["day_of_month"] = event.start.day
        event.recurrence.set_monthly(interval, **kwargs)

    if rules["FREQ"] == "WEEKLY":
        kwargs["first_day_of_week"] = "sunday"
        event.recurrence.set_weekly(interval, **kwargs)

    if rules["FREQ"] == "DAILY":
        event.recurrence.set_daily(interval, **kwargs)

    # The range dates are local dates, so Graph has to read them in the local zone
    try:
        event.recurrence.recurrence_time_zone = get_windows_tz(
            dt_util.get_default_time_zone()
        )
    except ZoneInfoNotFoundError:
        _LOGGER.debug(
            "No Windows time zone for %s, recurrence time zone left unchanged",
            dt_util.get_default_time_zone(),
        )


def _local_date(value, is_all_day):
    """Get the date as HA shows it; all day and naive values are already local."""
    if is_all_day or value.tzinfo is None:
        return value.date()
    return dt_util.as_local(value).date()


def _process_byday(byday):
    days = []
    for item in byday.split(","):
        if len(item) > 2:
            days.append(DAYS[item[2:4]])
            index = INDEXES[item[:2]]
        else:
            days.append(DAYS[item[:2]])
            index = None
    return days, index


def build_calendar_entity_id(device_id, entity_name):
    """Build calendar entity_id."""
    name = f"{entity_name}_{device_id}"
    return CALENDAR_ENTITY_ID_FORMAT.format(slugify(name))


async def async_delete_calendar(
    hass: HomeAssistant, config_entry: MS365ConfigEntry, calendar
):
    """Delete a calendar."""
    entity_id = build_calendar_entity_id(calendar, config_entry.data[CONF_ENTITY_NAME])
    ent_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
    for entity in entities:
        if entity.entity_id == entity_id:
            ent_reg.async_remove(entity_id)
            return
