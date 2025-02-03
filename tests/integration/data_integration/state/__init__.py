"""Tests for MS365 Calendar."""

import datetime

import zoneinfo

BASE_STATE_CAL1 = [
    {
        "summary": "Test event 2 calendar1",
        "start": datetime.date(2022, 10, 24),
        "end": datetime.date(2023, 10, 25),
        "all_day": True,
        "description": "Plain Text",
        "location": "Test Location",
        "categories": [],
        "sensitivity": "Private",
        "show_as": "Busy",
        "reminder": {"minutes": 0, "is_on": False},
        "attendees": [],
        "uid": "event2",
    },
    {
        "summary": "Test event 1 calendar1",
        "start": datetime.datetime(
            2020, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo(key="UTC")
        ),
        "end": datetime.datetime(
            2020, 1, 1, 23, 59, 59, tzinfo=zoneinfo.ZoneInfo(key="UTC")
        ),
        "all_day": False,
        "description": "Test",
        "location": "Test Location",
        "categories": [],
        "sensitivity": "Normal",
        "show_as": "Busy",
        "reminder": {"minutes": 30, "is_on": True},
        "attendees": [],
        "uid": "event1",
    },
]

BASE_STATE_CAL2 = [
    {
        "summary": "Test event calendar2",
        "start": datetime.datetime(
            2020, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo(key="UTC")
        ),
        "end": datetime.datetime(
            2020, 1, 2, 23, 59, 59, tzinfo=zoneinfo.ZoneInfo(key="UTC")
        ),
        "all_day": False,
        "description": "Test",
        "location": "Test Location",
        "categories": [],
        "sensitivity": "Normal",
        "show_as": "Busy",
        "reminder": {"minutes": 0, "is_on": False},
        "attendees": [],
        "uid": "event1",
    }
]
