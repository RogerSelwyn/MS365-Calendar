---
title: Sensors
nav_order: 8
---

# Sensors
## Calendar Sensor
The status of the calendar sensor indicates (on/off) whether there is an event on at the current time. The `message`, `all_day`, `start_time`, `end_time`, `location`, and `description` attributes provide details of the current or next event. A non-all-day event is favoured over all_day events.

The `data` attribute provides an array of events for the period defined by the `start_offset` and `end_offset` in `ms365_calendars_<entity_name>.yaml`. Individual array elements can be accessed using the template notation `states.calendar.<entity_name>_calendar.attributes.data[0...n]`.

Each event in `data` also has these read-only fields from MS Graph. What their values mean is in the Microsoft Graph documentation of the [location](https://learn.microsoft.com/en-us/graph/api/resources/location) and [event](https://learn.microsoft.com/en-us/graph/api/resources/event) resources:

- `location_details` - the `address`, `coordinates`, `type`, `email` and `uri` of the location, with only the parts that are filled in, or `null` when there is nothing beyond its name
- `locations` - each place of an event held in several, with its `name` and the same details, or `null` for an event in one place or none
- `online_meeting` - the `provider` and `join_url` of an online meeting, such as a Teams meeting, or `null` for any other event
- `web_link` - the link that opens the event in Outlook on the web
