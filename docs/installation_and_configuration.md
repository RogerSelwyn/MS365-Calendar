---
title: Installation and Configuration
nav_order: 4
---

# Installation and Configuration
## Installation
1. Ensure you have followed the [prerequisites instructions](./prerequisites.md)
    * Ensure you have a copy of the Client ID and the Client Secret **Value** (not the ID)
1. Optionally you can set up the [permissions](./permissions.md), alternatively you will be requested to approve permissions when you authenticate to MS 365.
1. Install this integration:
    * Recommended - see below, or
    * Manually - Copy [these files](https://github.com/RogerSelwyn/MS365-Calendar/tree/main/custom_components/ms365_calendar) to custom_components/ms365_calendar/.
1. Restart your Home Assistant instance to enable the integration
1. Add the integration via the `Devices & Services` dialogue. Follow the instructions in the install process (or see [Authentication](./authentication.md)) to establish the link between this integration and the Entra ID App Registration
    * A persistent token will be created in the hidden directory config/ms365_storage/.MS365-token-cache
    * The `ms365_calendars_<entity_name>.yaml` will be created under the config directory in the `ms365_storage` directory.
1. [Configure Calendars](./calendar_configuration.md)
1. Restart your Home Assistant instance.

**Note** If your installation does not complete authentication, or the sensors are not created, please go back and ensure you have accurately followed the steps detailed, also look in the logs to see if there are any errors. You can also look at the [errors page](./errors.md) for some other possibilities.

**Note** To configure a second account, add the integration again via the `Devices & Services` dialogue.

### HACS

1. Launch HACS
1. Search for "Microsoft 365 Calendar"
1. Select "Download"
1. Restart Home Assistant
1. Go to the Home Assistant Devices configuration page
1. Click "Add Integration"
1. Search for "Microsoft 365 Calendar"
1. Click on the result, and follow the prompts.


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

### Options variables

Key | Type | Required | Description
-- | -- | -- | --
`track_new_calendar` | `boolean` | `False` | If True (default), will automatically generate a calendar_entity when a new calendar is detected. The system scans for new calendars only on startup or reconfiguration/reload.
