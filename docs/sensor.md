---
title: Sensors
nav_order: 8
---

# Sensors
## Calendar Sensor
The status of the calendar sensor indicates (on/off) whether there is an event on at the current time. The `message`, `all_day`, `start_time`, `end_time`, `location` and `description` attributes provide details of the current or next event. A non-all-day event is favoured over all_day events. To act a set time before or after an event, use a [calendar trigger](https://www.home-assistant.io/integrations/calendar/#automation) with an `offset`.

The `data` attribute provides an array of events for the period defined by the `start_offset` and `end_offset` in `ms365_calendars_<entity_name>.yaml`. Individual array elements can be accessed using the template notation `states.calendar.<entity_name>_calendar.attributes.data[0...n]`.
