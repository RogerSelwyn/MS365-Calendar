---
title: Events
nav_order: 16
---

# Events

The attribute `ha_event` shows whether the event is triggered by an HA initiated action

##  Calendar Events

Events will be raised for the following items.

- ms365_calendar_create_calendar_event - Creation of a new event via the MS365 Calendar integration
- ms365_calendar_modify_calendar_event - Update of an event via the MS365 Calendar integration
- ms365_calendar_modify_calendar_recurrences - Update of a recurring event via the MS365 Calendar integration
- ms365_calendar_remove_calendar_event - Removal of an event via the MS365 Calendar integration
- ms365_calendar_remove_calendar_recurrences - Removal of a recurring event series via the MS365 Calendar integration
- ms365_calendar_respond_calendar_event - Response to an event via the MS365 Calendar integration

The events have the following general structure:

```yaml
event_type: ms365_calendar_create_calendar_event
data:
  event_id: >-
    AAMkAGQwYzQ5ZjZjLTQyYmItNDJmNy04NDNjLTJjYWY3NzMyMDBmYwBGAAAAAAC9VxHxYFrdCHSJkXtJ-BwCoiRErLbiNRJDCFyMjq4khAAY9v0_vAACoiRErLbiNRJDCFyMjq4khAAcZSY4SAAA=
  ha_event: true
origin: LOCAL
time_fired: "2023-02-19T15:29:01.962020+00:00"
context:
  id: 01GSN4NWGABVFQQWPP2D8G3CN8
  parent_id: null
  user_id: null
```

