"""Unit tests for work location helpers and service."""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from requests.exceptions import ConnectionError as RequestConnectionError, HTTPError

from custom_components.ms365_calendar.const import (
    CONF_API_COUNTRY,
    CONF_API_OPTIONS,
    CountryOptions,
)
from custom_components.ms365_calendar.integration.const_integration import (
    CONF_WORK_LOCATION,
    WORK_LOCATION_CAL_ID,
)
from custom_components.ms365_calendar.integration.setup_integration import (
    _add_work_location_calendar,
)
from custom_components.ms365_calendar.integration.sync.api import (
    MS365WorkLocationService,
    _friendly_work_location,
    _normalise_work_location_type,
)
from custom_components.ms365_calendar.integration.utils_integration import (
    format_event_data,
)
from custom_components.ms365_calendar.integration.work_location_integration import (
    get_day_location_state,
    get_day_work_location_types,
)

START = datetime(2026, 1, 5, 9, tzinfo=timezone.utc)
END = START + timedelta(hours=8)


def _occ(**kwargs):
    base = {
        "start": START,
        "end": END,
        "work_location_type": "office",
        "object_id": "id1",
        "recurrence_id": None,
        "location": None,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def _service(hass, occurrences=None, error=None):
    account = MagicMock()
    whl = MagicMock()
    if error:
        whl.occurrences_view.side_effect = error
    else:
        whl.occurrences_view.return_value = occurrences or []
    account.work_hours_and_locations.return_value = whl
    return MS365WorkLocationService(hass, account)


def _http_error(status):
    return HTTPError("boom", response=SimpleNamespace(status_code=status))


def test_day_types_and_state():
    """Test day type extraction and precedence."""
    events = [
        SimpleNamespace(start="bad"),
        SimpleNamespace(start=START + timedelta(days=1), work_location_type="office"),
        SimpleNamespace(start=START, work_location_type="Remote"),
        SimpleNamespace(start=START, body="Work location type: timeoff"),
        SimpleNamespace(start=START, body="Work location type:"),
        SimpleNamespace(start=START, body="nothing"),
    ]
    types = get_day_work_location_types(events, date(2026, 1, 5))
    assert types == {"remote", "timeoff", "unknown"}
    assert get_day_location_state(types) == "remote"
    assert get_day_location_state({"timeoff", "unknown"}) == "timeoff"
    assert get_day_location_state({"unknown"}) == "unknown"
    assert get_day_location_state({"office", "remote"}) == "office"


def test_helpers():
    """Test normalise and friendly helpers."""
    assert _normalise_work_location_type(None) == "unknown"
    assert _normalise_work_location_type(SimpleNamespace(value="office")) == "office"
    assert _normalise_work_location_type("remote") == "remote"
    assert _friendly_work_location("office", {"displayName": "HQ"}) == "HQ"
    assert _friendly_work_location("onsite", None) == "On site"
    assert _friendly_work_location("some_thing", None) == "Some Thing"


async def test_service_list_events(hass: HomeAssistant):
    """Test listing occurrences, including skipped and defaulted ones."""
    service = _service(
        hass,
        [
            _occ(),
            _occ(start=None),
            _occ(object_id=None, work_location_type=None, location={"displayName": "X"}),
        ],
    )
    await service.async_calendar_init()
    events = await service.async_list_events(START, END)
    assert len(events) == 2
    assert events[1].object_id.endswith("_X")


async def test_service_uninitialised(hass: HomeAssistant):
    """Test listing before init raises."""
    service = _service(hass)
    with pytest.raises(RuntimeError):
        service._list_work_location_occurrences(START, END)


async def test_init_ok(hass: HomeAssistant):
    """Test init with a working endpoint."""
    assert await _service(hass).async_calendar_init() is True


@pytest.mark.parametrize("status", [403, 404])
async def test_init_not_permitted(hass: HomeAssistant, status):
    """Test init disables the calendar when the endpoint is unavailable."""
    service = _service(hass, error=_http_error(status))
    assert await service.async_calendar_init() is False


@pytest.mark.parametrize(
    "error",
    [_http_error(500), HTTPError("no response"), RequestConnectionError("down")],
)
async def test_init_transient(hass: HomeAssistant, error):
    """Test init keeps the calendar on transient errors."""
    assert await _service(hass, error=error).async_calendar_init() is True


@pytest.mark.parametrize("country", list(CountryOptions))
def test_add_work_location_calendar(country):
    """Test calendar is only added for the default country."""
    entry = SimpleNamespace(
        data={CONF_API_OPTIONS: {CONF_API_COUNTRY: country}},
        options={CONF_WORK_LOCATION: True},
    )
    calendars = {}
    _add_work_location_calendar(entry, calendars)
    assert (WORK_LOCATION_CAL_ID in calendars) == (country == CountryOptions.DEFAULT)


def test_add_work_location_calendar_skipped():
    """Test shared mailbox and disabled option skip the calendar."""
    calendars = {}
    _add_work_location_calendar(
        SimpleNamespace(data={"shared_mailbox": "a@b.c"}, options={CONF_WORK_LOCATION: True}),
        calendars,
    )
    _add_work_location_calendar(SimpleNamespace(data={}, options={}), calendars)
    assert calendars == {}


def test_format_event_data_string_location():
    """Test a plain string location is handled."""
    event = SimpleNamespace(
        object_id="1",
        subject="s",
        start=START,
        end=END,
        location="Office",
        is_all_day=False,
        attendees=SimpleNamespace(
            _Attendees__attendees=[
                SimpleNamespace(
                    address="a@b.c",
                    attendee_type=SimpleNamespace(value="required"),
                    response_status=SimpleNamespace(status=None),
                )
            ]
        ),
        work_location_type="office",
    )
    data = format_event_data(event)
    assert data["location"] == "Office"
    assert data["attendees"][0]["status"] is None
    assert data["work_location_type"] == "office"
