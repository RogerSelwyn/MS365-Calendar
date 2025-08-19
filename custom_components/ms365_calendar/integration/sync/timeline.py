"""A Timeline is a set of events on a calendar."""

from collections.abc import Generator, Iterable
from datetime import datetime, timedelta  # time

from homeassistant.util import dt as dt_util
from ical.iter import (
    MergedIterable,
    SortableItem,
    SortableItemTimeline,
    SortableItemValue,
    SortedItemIterable,
)
from ical.timespan import Timespan
from O365.calendar import Event  # pylint: disable=no-name-in-module)


class MS365Timeline(SortableItemTimeline[Event]):
    """A set of events on a calendar.
    A timeline is created by the local sync API and not instantiated directly.
    """

    # def __init__(self, iterable: Iterable[SortableItem[Timespan, Event]]) -> None:
    #     super().__init__(iterable)


def timespan_of(event: Event) -> Timespan:
    """Return a timespan representing the event start and end."""
    # if tzinfo is None:
    #     tzinfo = dt_util.UTC
    # return Timespan.of(
    #     normalize(event.start, tzinfo),
    #     normalize(event.end, tzinfo),
    # )
    if event.is_all_day:
        return Timespan.of(
            dt_util.start_of_local_day(event.start),
            dt_util.start_of_local_day(event.end),
        )
    return Timespan.of(event.start, event.end)


def calendar_timeline(events: list[Event], tzinfo: datetime.tzinfo) -> MS365Timeline:
    """Create a timeline for events on a calendar, including recurrence."""
    normal_events: list[Event] = []
    for event in events:
        normal_events.append(event)

    def sortable_items() -> Generator[SortableItem[Timespan, Event], None, None]:
        nonlocal normal_events
        for event in normal_events:
            yield SortableItemValue(timespan_of(event), event)

    iters: list[Iterable[SortableItem[Timespan, Event]]] = []
    iters.append(SortedItemIterable(sortable_items, tzinfo))

    return MS365Timeline(MergedIterable(iters))


# def normalize(date, tzinfo: datetime.tzinfo) -> datetime:
#     """Convert date or datetime to a value that can be used for comparison."""
#     value = date
#     if not isinstance(value, datetime):
#         value = datetime.combine(value, time.min)
#     if value.tzinfo is None:
#         value = value.replace(tzinfo=(tzinfo if tzinfo else dt_util.UTC))
#     return value
