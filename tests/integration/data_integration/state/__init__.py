"""Tests for MS365 Calendar."""

import datetime as dt
import zoneinfo

BASE_STATE_CAL1 = [
    {
        "summary": "Test event 1 calendar1",
        "start": dt.datetime(2020, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo(key="UTC")),
        "end": dt.datetime(2020, 1, 2, 23, 59, 59, tzinfo=zoneinfo.ZoneInfo(key="UTC")),
        "all_day": False,
        "description": "Test",
        "location": "Test Location",
        "categories": [],
        "sensitivity": "Normal",
        "show_as": "Busy",
        "reminder": {"minutes": 30, "is_on": True},
        "organizer": "john@nomail.com",
        "attendees": [
            {"email": "jane@nomail.com", "type": "required", "status": "not_responded"}
        ],
        "uid": "event1",
        "web_link": None,
    },
    {
        "summary": "Test event 2 calendar1",
        "start": dt.date(2020, 1, 1),
        "end": dt.date(2020, 1, 2),
        "all_day": True,
        "description": "Plain Text",
        "location": "Test Location",
        "categories": [],
        "sensitivity": "Private",
        "show_as": "Busy",
        "reminder": {"minutes": 0, "is_on": False},
        "attendees": [],
        "organizer": "",
        "uid": "event2",
        "web_link": None,
    },
]

BASE_STATE_CAL2 = [
    {
        "summary": "Test event calendar2",
        "start": dt.datetime(2020, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo(key="UTC")),
        "end": dt.datetime(2020, 1, 2, 23, 59, 59, tzinfo=zoneinfo.ZoneInfo(key="UTC")),
        "all_day": False,
        "description": "Test",
        "location": "Test Location",
        "categories": [],
        "sensitivity": "Normal",
        "show_as": "Busy",
        "reminder": {"minutes": 0, "is_on": False},
        "attendees": [],
        "organizer": "",
        "uid": "event1",
        "web_link": None,
    }
]

# The location fields of each event in calendar1_calendar_view_locations, by uid
LOCATION_STATE = {
    "address": {
        "location": "Fourth Coffee",
        "locations": [
            {
                "name": "Fourth Coffee",
                "type": "localBusiness",
                "address": {
                    "street": "4567 Main St",
                    "city": "Redmond",
                    "state": "WA",
                    "postal_code": "98052",
                    "country": "United States",
                },
                "coordinates": {"latitude": 47.672, "longitude": -122.103},
                "uri": "https://www.bingapis.com/api/v6/localbusinesses/fourthcoffee",
            }
        ],
    },
    "room": {
        "location": "Room 1",
        "locations": [
            {
                "name": "Room 1",
                "type": "conferenceRoom",
                "address": {"city": "Utrecht"},
                "email": "room1@nomail.com",
            }
        ],
    },
    "several": {
        "location": "Room 1; Head office; Home office",
        "locations": [
            {"name": "Room 1", "type": "conferenceRoom", "email": "room1@nomail.com"},
            {
                "name": "Head office",
                "type": "businessAddress",
                "address": {
                    "street": "1 Station Square",
                    "city": "Utrecht",
                    "postal_code": "3511 ED",
                    "country": "Netherlands",
                },
                "coordinates": {"latitude": 52.089, "longitude": 5.11},
            },
            {"name": "Home office", "type": "default"},
        ],
    },
    "name_only": {
        "location": "Dentist",
        "locations": [{"name": "Dentist", "type": "default"}],
    },
    "no_location": {
        "location": "",
    },
}

WEB_LINK = "https://outlook.office365.com/owa/?itemid={}&exvsurl=1&path=/calendar/item"

# The online meeting and web link of each event in calendar1_calendar_view_meetings,
# by uid
MEETING_STATE = {
    "teams": {
        "online_meeting": {
            "provider": "teams_for_business",
            "join_url": "https://teams.microsoft.com/l/meetup-join/19%3ameeting_"
            "ZmFrZS1tZWV0aW5nLWlk%40thread.v2/0?context=%7b%22Tid%22%3a%22"
            "fake-tenant-id%22%2c%22Oid%22%3a%22fake-user-id%22%7d",
        },
        "web_link": WEB_LINK.format("teams"),
    },
    "not_set_up": {
        "online_meeting": {
            "provider": "teams_for_business",
            "join_url": None,
        },
        "web_link": WEB_LINK.format("not_set_up"),
    },
    "in_person": {
        "web_link": WEB_LINK.format("in_person"),
    },
}
