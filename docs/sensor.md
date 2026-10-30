---
title: Sensors
nav_order: 8
---

# Sensors
## Calendar Sensor
The status of the calendar sensor indicates (on/off) whether there is an event on at the current time. The `message`, `all_day`, `start_time`, `end_time`, `location`, and `description` attributes provide details of the current or next event. A non-all-day event is favoured over all_day events.

The `data` attribute provides an array of events for the period defined by the `start_offset` and `end_offset` in `ms365_calendars_<entity_name>.yaml`. Individual array elements can be accessed using the template notation `states.calendar.<entity_name>_calendar.attributes.data[0...n]`.

### Location details

`location` is the name of the place, as Outlook shows it. When MS Graph knows more about the place, such as for an address picked from the suggestions in Outlook or for a booked room, `location_details` has it, with only the parts that are filled in:

- `address` - `street`, `city`, `state`, `postal_code` and `country`
- `coordinates` - `latitude` and `longitude`
- `type` - the kind of place, such as `conference_room`, `street_address`, `business_address` or `local_business`. A place typed in as plain text has no type
- `email` - the email address of a room
- `uri` - a link for the place

`location_details` is `null` when there is nothing more than the name.

An event can be held in several places, such as a room and a home office. `location` then has all their names, separated by `; `, and `locations` lists each place with its `name` and the same details. For an event in one place, or none, `locations` is `null`.

```yaml
location: Fourth Coffee
location_details:
  address:
    street: 4567 Main St
    city: Redmond
    state: WA
    postal_code: "98052"
    country: United States
  coordinates:
    latitude: 47.672
    longitude: -122.103
  type: local_business
locations: null
```

```yaml
location: Room 1; Head office
location_details: null
locations:
  - name: Room 1
    type: conference_room
    email: room1@example.com
  - name: Head office
    address:
      street: 1 Station Square
      city: Utrecht
      postal_code: 3511 ED
      country: Netherlands
```

For example, this template gives the address of the first event as one line, such as for a travel time to it. It gives nothing when there is no event in the period, or no address:

{% raw %}
```
{% set events = state_attr('calendar.user_primary', 'data') or [] %}
{% set details = events[0].location_details if events else none %}
{% if details and details.address is defined %}
  {{ details.address.values() | join(', ') }}
{% endif %}
```
{% endraw %}

### Online meetings and links

`online_meeting` is set for an online meeting, such as a Teams meeting, and is `null` for any other event. It has:

- `provider` - the service of the meeting: `teams_for_business`, `skype_for_business` or `skype_for_consumer`, or `null` when MS Graph does not say which
- `join_url` - the link to join the meeting, or `null` when MS365 has none for it. This is the join link MS Graph has for the meeting. Some older meetings, such as Skype meetings, only have a link in the older `onlineMeetingUrl` field of MS Graph, which is then used

`online_meeting` only comes from what MS365 has on the meeting itself. A link to another service, such as Zoom or Webex, that is only in the text of the event is not looked for, so such an event has `online_meeting` `null`.

`web_link` is the link that opens the event in Outlook on the web. It only opens the event for someone who can open that calendar there.

```yaml
online_meeting:
  provider: teams_for_business
  join_url: https://teams.microsoft.com/l/meetup-join/19%3ameeting_...
web_link: https://outlook.office365.com/owa/?itemid=...&exvsurl=1&path=/calendar/item
```

Anyone who has the join link can use it to join the meeting, or wait in its lobby, so take care where you show or send it, such as in a notification or on a dashboard others can see. The `data` attribute is not kept in the history of the calendar, and the integration's diagnostics have no event data, so the links are in neither.

For example, this template gives the join link of the first online meeting in the period that has one, such as for a button on a dashboard. It gives nothing when there is none:

{% raw %}
```
{% set events = state_attr('calendar.user_primary', 'data') or [] %}
{% set meetings = events | map(attribute='online_meeting') | select | selectattr('join_url') | list %}
{{ meetings[0].join_url if meetings else '' }}
```
{% endraw %}
