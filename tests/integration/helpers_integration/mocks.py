"""Mock setup."""

from datetime import timedelta

from ...helpers.utils import mock_call, utcnow
from ..const_integration import CN21VURL, URL


class MS365Mocks:
    """Standard mocks."""

    def standard_mocks(self, requests_mock):
        """Setup the standard mocks."""
        mock_call(requests_mock, URL.OPENID, "openid")
        mock_call(requests_mock, URL.ME, "me")
        mock_call(requests_mock, URL.CALENDARS, "calendars")
        mock_call(requests_mock, URL.CALENDARS, "calendar1", "calendar1")
        mock_call(
            requests_mock,
            URL.CALENDARS,
            "calendar1_calendar_view",
            "calendar1/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        mock_call(requests_mock, URL.CALENDARS, "calendar2", "group:calendar2")
        mock_call(
            requests_mock,
            URL.GROUP_CALENDARS,
            "calendar2_calendar_view",
            "calendar2/calendar/calendarView",
            start=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=2)).strftime("%Y-%m-%d"),
        )
        mock_call(requests_mock, URL.CALENDARS, "calendar3", "calendar3")
        mock_call(
            requests_mock,
            URL.CALENDARS,
            "calendar3_calendar_view",
            "calendar3/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )

    def cn21v_mocks(self, requests_mock):
        """Setup the standard mocks."""
        mock_call(requests_mock, CN21VURL.DISCOVERY, "discovery")
        mock_call(requests_mock, CN21VURL.OPENID, "openid")
        mock_call(requests_mock, CN21VURL.ME, "me")

    def shared_mocks(self, requests_mock):
        """Setup the standard mocks."""
        mock_call(requests_mock, URL.OPENID, "openid")
        mock_call(requests_mock, URL.ME, "me")
        mock_call(requests_mock, URL.SHARED_CALENDARS, "calendars")
        mock_call(requests_mock, URL.SHARED_CALENDARS, "calendar1", "calendar1")
        mock_call(
            requests_mock,
            URL.SHARED_CALENDARS,
            "calendar1_calendar_view",
            "calendar1/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        mock_call(requests_mock, URL.CALENDARS, "calendar2", "group:calendar2")
        mock_call(
            requests_mock,
            URL.GROUP_CALENDARS,
            "calendar2_calendar_view",
            "calendar2/calendar/calendarView",
        )
        mock_call(requests_mock, URL.SHARED_CALENDARS, "calendar3", "calendar3")
        mock_call(
            requests_mock,
            URL.SHARED_CALENDARS,
            "calendar3_calendar_view",
            "calendar3/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )

    def no_events_mocks(self, requests_mock):
        """Setup the standard mocks."""
        _generic_mocks(requests_mock)
        mock_call(
            requests_mock,
            URL.CALENDARS,
            "calendar1_calendar_view_none",
            "calendar1/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )

    def all_day_event_mocks(self, requests_mock):
        """Setup the standard mocks."""
        _generic_mocks(requests_mock)
        mock_call(
            requests_mock,
            URL.CALENDARS,
            "calendar1_calendar_view_all_day",
            "calendar1/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )

    def started_event_mocks(self, requests_mock):
        """Setup the standard mocks."""
        _generic_mocks(requests_mock)
        mock_call(
            requests_mock,
            URL.CALENDARS,
            "calendar1_calendar_view_started",
            "calendar1/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )

    def not_started_event_mocks(self, requests_mock):
        """Setup the standard mocks."""
        _generic_mocks(requests_mock)
        mock_call(
            requests_mock,
            URL.CALENDARS,
            "calendar1_calendar_view_not_started",
            "calendar1/calendarView",
            start=utcnow().strftime("%Y-%m-%d"),
            end=(utcnow() + timedelta(days=1)).strftime("%Y-%m-%d"),
        )


MS365MOCKS = MS365Mocks()


def _generic_mocks(requests_mock):
    mock_call(requests_mock, URL.OPENID, "openid")
    mock_call(requests_mock, URL.ME, "me")
    mock_call(requests_mock, URL.CALENDARS, "calendars_one")
    mock_call(requests_mock, URL.CALENDARS, "calendar1", "calendar1")
