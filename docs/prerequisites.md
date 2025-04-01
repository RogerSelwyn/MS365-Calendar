---
title: Prerequisites
nav_order: 2
---

# Prerequisites

## Note - Personal accounts
Since the middle of 2024, Microsoft has mandated that any new app registrations must be created within an Entra ID directory. You will need to sign up for [Azure](https://azure.microsoft.com/en-gb/free) on a pay as you go basis, where Microsoft Entra ID is indicated as always being free.

## Getting the client ID and client secret
To allow authentication, you first need to register your application at Entra ID App Registrations:

1. Login at [Entra ID Portal (App Registrations)](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade). Personal accounts may receive an authentication notification that can be ignored.

2. Create a new App Registration. Give it a name (e.g., `Home Assistant MS365`). 

   - In Supported account types, choose one of the following as needed by your setup:
      * `Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)`.   
      * `Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant)` 

      **Do not use the following:** 
      * `Accounts in this organizational directory only (xxxxx only - Single tenant)` 
      * `Personal Microsoft accounts only`

   - Under `Redirect URI (optional)`. Click `Select a platform`. Select `Web`. Set Redirect URI to `https://login.microsoftonline.com/common/oauth2/nativeclient` (`https://login.partner.microsoftonline.cn/common/oauth2/nativeclient` for 21Vianet). Leave the other fields blank and click Configure.

      An alternate method of authentication is available which requires Internet access to your HA instance. The alternate method is simpler to use when authenticating, but is more complex to set up correctly. See [Authentication](./authentication.md) section for more details.

3. Click `Register`

4. From the Overview page, copy the Application (client) ID.

5. Click `Certificates & secrets` in the Manage section on the left side or `Add a certificate or secret` in the main section. Click `New client secret`. Give it a Description (e.g., 'Home Assistant MS365') and Set the expiration as desired (this appears to be limited to 2 years) and Click `Add`. Copy the **Value** of the client secret now (NOT the Secret ID), it will be hidden later on.  If you lose track of the secret, return here to generate a new one.

6. Click `API permissions` in the Manage section on the left side. Click `Add a permission`, then `Microsoft Graph`, then `Delegated permissions`, add the permissions as detailed on the [permissions page](./permissions.md), and Cliick `Add permissions`.
