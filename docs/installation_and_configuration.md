---
title: Installation and Configuration
nav_order: 4
---

# Installation and Configuration
This page details the configuration details for this integration. General instructions can be found on the MS365 Home Assistant [Installation and Configuration](https://rogerselwyn.github.io/MS365-HomeAssistant/installation_and_configuration.html) page.

### Configuration variables

Key | Type | Required | Description
-- | -- | -- | --
`entity_name` | `string` | `True` | Uniquely identifying name for the account. Calendars entity names will be suffixed with this. `calendar.calendar_account1`. Do not use email address or spaces.
`client_id` | `string` | `True` | Client ID from your Entra ID App Registration.
`client_secret` | `string` | `True` | Client Secret from your Entra ID App Registration.
`alt_auth_method` | `boolean` | `False` | If False (default), authentication is not dependent on internet access to your HA instance. [See Authentication](./authentication.md)
`enable_update` | `boolean` | `False` | If True (**default is False**), this will enable the various services that allow updates to calendars
`basic_calendar` | `boolean` | `False` | If True (**default is False**), the permission requested will be `calendar.ReadBasic`. `enable_update: true` = true cannot be used if `basic_calendar: true`
`groups` | `boolean` | `False` | If True (**default is False**), will enable support for group calendars. No discovery is performed. You will need to know how to get the group ID from the MS Graph API. *Not for use on shared mailboxes*
`shared_mailbox` | `string` | `False` | Email address or ID of shared mailbox (This should not be the same email address as the loggin in user).

#### Advanced API Options

These options will only be relevant for users in very specific circumstances.

Key | Type | Required | Description
-- | -- | -- | --
`country` | `string` | `True` | Selection of an alternate country specific API. Currently only 21Vianet from China.

### Options

Key | Type | Required | Description
-- | -- | -- | --
`calendar_list` | `list[string]` | `False` | The selectable list of calendars for which calendar entities will be created.
`track_new_calendar` | `boolean` | `False` | If True (default), will automatically generate a calendar_entity when a new calendar is detected. The system scans for new calendars only on startup or reconfiguration/reload.

### Advanced Options

Key | Type | Required | Description
-- | -- | -- | --
`update_interval` | `integer` | `False` | How often in seconds that events will be retrieved and synced to store. Default 60. Range: 15 - 600
`days_backward` | `integer` | `False` | The days backward from `now` for which events will be synced to store. Default -8. Range: -90 - 90
`days_forward` | `integer` | `False` | The days forward from `now` for which events will be synced to store. Default 8. Range: -90 - 90
