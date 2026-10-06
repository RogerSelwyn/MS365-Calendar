---
title: Calendar Panel
nav_order: 17
---

Creation, modification deletion of events is possible via the Calendar Panel. This UI allows you to create recurring events, which is not possible via the HA services methods. 

If you choose to delete 'Delete All Future Events', it will delete the whole series not just future events. This is due to the differences between MS365_Calendar and the iCal specification that the core calendar is built on.

For the same reason, if you choose to update 'This and all future events', the change is made to the whole series, including past events. The series keeps its own dates, so only a change to the title, description, location, time of day or length is applied; changing the date this way is not possible.

The Calendar Panel only shows the text of an event's description. If you leave the description unchanged, the original description, including its formatting and links (such as the details to join an online meeting), is kept. If you change it, the event's description is replaced by the plain text you entered.

The location works the same way. Only its name is shown, so if you leave it unchanged the original location, such as a meeting room with its address, is kept. If you change it, the location is replaced by the name you entered.
