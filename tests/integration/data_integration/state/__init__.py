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
        "location_details": None,
        "locations": None,
        "online_meeting": None,
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
        "location_details": None,
        "locations": None,
        "online_meeting": None,
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
        "location_details": None,
        "locations": None,
        "online_meeting": None,
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
        "location_details": {
            "address": {
                "street": "4567 Main St",
                "city": "Redmond",
                "state": "WA",
                "postal_code": "98052",
                "country": "United States",
            },
            "coordinates": {"latitude": 47.672, "longitude": -122.103},
            "type": "local_business",
            "uri": "https://www.bingapis.com/api/v6/localbusinesses/fourthcoffee",
        },
        "locations": None,
    },
    "room": {
        "location": "Room 1",
        "location_details": {
            "address": {"city": "Utrecht"},
            "type": "conference_room",
            "email": "room1@nomail.com",
        },
        "locations": None,
    },
    "several": {
        "location": "Room 1; Head office; Home office",
        "location_details": None,
        "locations": [
            {"name": "Room 1", "type": "conference_room", "email": "room1@nomail.com"},
            {
                "name": "Head office",
                "address": {
                    "street": "1 Station Square",
                    "city": "Utrecht",
                    "postal_code": "3511 ED",
                    "country": "Netherlands",
                },
                "coordinates": {"latitude": 52.089, "longitude": 5.11},
                "type": "business_address",
            },
            {"name": "Home office"},
        ],
    },
    "name_only": {
        "location": "Dentist",
        "location_details": None,
        "locations": None,
    },
    "no_location": {
        "location": "",
        "location_details": None,
        "locations": None,
    },
}

TEAMS_JOIN_URL = (
    "https://teams.microsoft.com/l/meetup-join/19%3ameeting_ZmFrZS1tZWV0aW5nLWlk"
    "%40thread.v2/0?context=%7b%22Tid%22%3a%22fake-tenant-id%22%2c%22Oid%22%3a"
    "%22fake-user-id%22%7d"
)
WEB_LINK = "https://outlook.office365.com/owa/?itemid={}&exvsurl=1&path=/calendar/item"

# The online meeting and web link of each event in calendar1_calendar_view_meetings,
# by uid
MEETING_STATE = {
    "teams": {
        "online_meeting": {
            "provider": "teams_for_business",
            "join_url": TEAMS_JOIN_URL,
        },
        "web_link": WEB_LINK.format("teams"),
    },
    "skype": {
        "online_meeting": {
            "provider": "skype_for_business",
            "join_url": "https://meet.lync.com/nomail/john/SKYPE123",
        },
        "web_link": WEB_LINK.format("skype"),
    },
    # The join link is used rather than the old link kept in onlineMeetingUrl
    "moved_to_teams": {
        "online_meeting": {
            "provider": "teams_for_business",
            "join_url": "https://teams.microsoft.com/l/meetup-join/19%3ameeting_"
            "bW92ZWQtbWVldGluZy1pZA%40thread.v2/0?context=%7b%22Tid%22%3a%22"
            "fake-tenant-id%22%2c%22Oid%22%3a%22fake-user-id%22%7d",
        },
        "web_link": WEB_LINK.format("moved_to_teams"),
    },
    "link_only": {
        "online_meeting": {
            "provider": None,
            "join_url": "https://meet.nomail.com/john/LINK123",
        },
        "web_link": WEB_LINK.format("link_only"),
    },
    "in_person": {
        "online_meeting": None,
        "web_link": WEB_LINK.format("in_person"),
    },
}
