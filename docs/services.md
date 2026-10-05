---
title: Services
nav_order: 15
---

# Services

##  Calendar Services
### ms365_calendar.create_calendar_event
Create an event in the specified calendar - All parameters are shown in the available parameter list on the Developer Tools/Services tab.
### ms365_calendar.modify_calendar_event
Modify an event in the specified calendar - All parameters are shown in the available parameter list on the Developer Tools/Services tab. Not possible for group calendars.
### ms365_calendar.remove_calendar_event
Remove an event in the specified calendar - All parameters are shown in the available parameter list on the Developer Tools/Services tab. Not possible for group calendars.
### ms365_calendar.respond_calendar_event
Respond to an event in the specified calendar - All parameters are shown in the available parameter list on the Developer Tools/Services tab. Not possible for group calendars.
### ms365_calendar.get_calendar_events
Get the events in a time range, with the same per-event detail as the calendar entity's `data` attribute - including `attendees` (email, type, response status), `organizer`, `categories`, `sensitivity`, `show_as` and `uid`. Use it with `response_variable`. Unlike the core `calendar.get_events` action, which only returns summary, start, end, description and location, and unlike the `data` attribute, which only covers the entity's `start_offset`/`end_offset` window.

#### Example create event service call

```yaml
service: ms365_calendar.create_calendar_event
target:
  entity_id:
    - calendar.user_primary
data:
  subject: Clean up the garage
  start: 2023-01-01T12:00:00+0000
  end: 2023-01-01T12:30:00+0000
  body: Remember to also clean out the gutters
  location: 1600 Pennsylvania Ave Nw, Washington, DC 20500
  sensitivity: Normal
  show_as: Busy
  attendees:
    - email: test@example.com
      type: Required
```

Response - Note uid is shown as an attribute of the entity_id since multiple entities can potentially be actioned at the same time.

```yaml
calendar.user_primary:
  uid: >-
    long_guid
```

#### Example get events service call

```yaml
action: ms365_calendar.get_calendar_events
target:
  entity_id: calendar.user_primary
data:
  start_date_time: "{{ now().isoformat() }}"
  end_date_time: "{{ (now() + timedelta(days=3)).isoformat() }}"
response_variable: events
```

The response is keyed by entity: `events['calendar.user_primary'].events` is a list of events, each with `summary`, `start`, `end`, `all_day`, `description`, `location`, `categories`, `sensitivity`, `show_as`, `reminder`, `organizer`, `attendees` and `uid`.
