---
title: Permissions
nav_order: 3
---

# Permissions

This page details the permissions for this integration. General instructions can be found on the MS365 Home Assistant [Permissions](https://rogerselwyn.github.io/MS365-HomeAssistant/permissions.html) page.

*Note the requirement for `.Shared` permissions for shared mailbox calendars*

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
   

