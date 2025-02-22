---
title: Authentication
nav_order: 5
---

# Authentication

The Primary method of authentication is the simplest to configure and requires no access from the internet to your HA instance, therefore is the most secure method. It has slightly more steps to follow when authenticating.

The alternate method is more complex to set up, since the Entra ID App Registration that is created in the prerequisites' section must be configured to enable authentication from your HA instance whether located in your home network or utilising a cloud service such as Nabu Casa. The actual authentication is slightly simpler with fewer steps.

During setup, the difference in configuration between each method is the value of the redirect URI on your Entra ID App Registration. The authentication steps for each method are shown below.

## Primary (default) authentication method
This requires *alt_auth_method* to be set to *False* or be not present and the redirect URI in your Entra ID App Registration app set to `https://login.microsoftonline.com/common/oauth2/nativeclient` (`https://login.partner.microsoftonline.cn/common/oauth2/nativeclient` for 21Vianet).

Do not use Safari on MacOS for this process, you will not be returned the URL at step 3 that you need.

When adding the integration, leave `Use alternate authentication` disabled.
1. When prompted click the `Link MS365 account` link.
1. Login on the Microsoft page; when prompted, authorize the app you created
1. Copy the URL from the browser URL bar.
1. Insert into the "Returned URL" field
1. Click `Submit`.

## Alternate authentication method
This requires the `Use alternate authentication` to be enabled and the redirect URI in your Entra ID App Registration set to `https://<your_home_assistant_url_or_local_ip>/api/ms365` (Nabu Casa users should use `https://<NabuCasaBaseAddress>/api/ms365_calendar` instead).

When adding the integration, enable `Use alternate authentication`.
1. When prompted click the `Link MS365 account` link.
1. Login on the Microsoft page; when prompted, authorize the app you created
1. If required, close the window when the message "This window can be closed" appears.
1. Click `I authorized successfully`

## Multi-Factor Authentication (MFA)
If you are using Multi-factor Authentication (MFA), you may find you also need to add `https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize` to your redirect URIs.

## Re-authentication
If you need to re-authenticate for any reason, for instance if you want to change features, just click on `Reconfigure` in the three dot menu of the integration, and it will take you through the process.
