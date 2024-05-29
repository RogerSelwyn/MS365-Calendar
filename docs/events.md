---
title: Events
nav_order: 16
---

# Events

The attribute `ha_event` shows whether the event is triggered by an HA initiated action

##  Calendar Events

Events will be raised for the following items.

- o365_create_calendar_event - Creation of a new event via the O365 integration
- o365_modify_calendar_event - Update of an event via the O365 integration
- o365_modify_calendar_recurrences - Update of a recurring event via the O365 integration
- o365_remove_calendar_event - Removal of an event via the O365 integration
- o365_remove_calendar_recurrences - Removal of a recurring event series via the O365 integration
- o365_respond_calendar_event - Response to an event via the O365 integration

The events have the following general structure:

```yaml
event_type: o365_create_calendar_event
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

