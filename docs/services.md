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

