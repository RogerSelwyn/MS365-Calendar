"""Shared work-location helper logic."""

from datetime import datetime

from homeassistant.util import dt as dt_util

WORK_LOCATION_TYPE_OFFICE = "office"
WORK_LOCATION_TYPE_REMOTE = "remote"
WORK_LOCATION_TYPE_TIMEOFF = "timeoff"
WORK_LOCATION_TYPE_UNKNOWN = "unknown"


def get_day_work_location_types(events, target_date) -> set[str]:
    """Return work-location types for events that start on target_date."""
    types: set[str] = set()
    for event in events:
        start = getattr(event, "start", None)
        if not isinstance(start, datetime):
            continue
        start_local = dt_util.as_local(start).date()
        if start_local != target_date:
            continue
        types.add(_extract_work_location_type(event))
    return types


def get_day_location_state(types: set[str]) -> str:
    """Return a single day-level location value with stable precedence."""
    if WORK_LOCATION_TYPE_OFFICE in types:
        return WORK_LOCATION_TYPE_OFFICE
    if WORK_LOCATION_TYPE_REMOTE in types:
        return WORK_LOCATION_TYPE_REMOTE
    if WORK_LOCATION_TYPE_TIMEOFF in types:
        return WORK_LOCATION_TYPE_TIMEOFF
    return WORK_LOCATION_TYPE_UNKNOWN


def _extract_work_location_type(event) -> str:
    work_location_type = getattr(event, "work_location_type", None)
    if isinstance(work_location_type, str) and work_location_type:
        return work_location_type.lower()
    body = str(getattr(event, "body", "") or "")
    marker = "work location type:"
    if marker not in body.lower():
        return WORK_LOCATION_TYPE_UNKNOWN
    value = body.split(":", 1)[1].strip().lower()
    return value or WORK_LOCATION_TYPE_UNKNOWN
