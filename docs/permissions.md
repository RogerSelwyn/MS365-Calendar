---
title: Permissions
nav_order: 3
---

# Permissions

Under "API Permissions" click Add a permission, then Microsoft Graph, then Delegated permission, and add the permissions as detailed in the list and table below:
  * Calendar - For calendars *Note the requirement for `.Shared` permissions for shared mailbox calendars*


   | Feature  | Permissions                | Update | MS Graph Description                                  | Notes |
   |----------|----------------------------|:------:|-------------------------------------------------------|-------|
   | All      | offline_access             |        | *Maintain access to data you have given it access to* |       |
   | All      | User.Read                  |        | *Sign in and read user profile*                       |       |
   | Calendar | Calendars.ReadBasic        |        | *Read basic details of user calendars*                | Used when `basic_calendar` is set to `true` |
   | Calendar | Calendars.Read             |        | *Read user calendars*                                 |       |
   | Calendar | Calendars.ReadWrite        | Y      | *Read and write user calendars*                       |       |
   | Calendar | Calendars.Read.Shared      |        | *Read user and shared calendars*                      | For shared mailboxes |
   | Calendar | Calendars.ReadWrite.Shared | Y      | *Read and write user and shared calendars*            | For shared mailboxes |
   | Group Calendar | Group.Read.All       |        | *Read all groups*                                     | Not supported in shared mailboxes |
   | Group Calendar | Group.ReadWrite.All  | Y      | *Read and write all groups*                           | Not supported in shared mailboxes |
   

## Changing Features and Permissions
If you decide to enable new features in the integration, or decide to change from read only to read/write, you will very likely get a warning message similar to the following in your logs.

`Minimum required permissions not granted: ['Tasks.Read', ['Tasks.ReadWrite']]`

You will need to delete as detailed on the [token page](./token.md)
