"""Constants."""

from enum import StrEnum

ATTR_DATA = "data"
ATTR_ERROR = "error"
ATTR_STATE = "state"

AUTH_CALLBACK_NAME = "api:ms365"
AUTH_CALLBACK_PATH_ALT = "/api/ms365"

CONF_ENTITY_NAME = "entity_name"
CONF_ALT_AUTH_METHOD = "alt_auth_method"
CONF_API_COUNTRY = "country"
CONF_API_OPTIONS = "api_options"
CONF_AUTH_URL = "auth_url"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"  # nosec
CONF_ENABLE_UPDATE = "enable_update"
CONF_ENTITY_KEY = "entity_key"
CONF_ENTITY_TYPE = "entity_type"
CONF_FAILED_PERMISSIONS = "failed_permissions"
CONF_SHARED_MAILBOX = "shared_mailbox"
CONF_URL = "url"

CONST_UTC_TIMEZONE = "UTC"

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"

EVENT_HA_EVENT = "ha_event"

MS365_STORAGE = "ms365_storage"
MS365_STORAGE_TOKEN = ".MS365-token-cache"

PERM_USER_READ = "User.Read"
PERM_SHARED = ".Shared"
PERM_BASE_PERMISSIONS = [PERM_USER_READ]

ERROR_IMPORTED_DUPLICATE = "Entry already imported for '%s' - '%s'"
ERROR_INVALID_SHARED_MAILBOX = (
    "Login email address '%s' should not be "
    + "entered as shared email address, config attribute removed."
)
SECRET_EXPIRED = (
    "Client Secret expired for account: %s. "
    + "Create new Client Secret in Entra ID App Registration."
)
TOKEN_DELETED = (
    "Token %s has been deleted as part of upgrade"
    + " - please re-configure to re-authenticate"
)
TOKEN_ERROR = "Token error for account: %s. Error - %s"
TOKEN_ERROR_CORRUPT = (
    "Token file corrupted for integration '%s', unique identifier '%s', "
    + "please delete token, re-configure and re-authenticate - %s"
)
TOKEN_ERROR_FILE = (
    "Token file retrieval error, check log for errors from O365. "
    + "Ensure token has not expired and you are using secret value not secret id."
)
TOKEN_ERROR_LEGACY = (
    "Token no longer valid for integration '%s', unique identifier '%s', "
    + "please delete token, re-configure and re-authenticate - %s"
)
TOKEN_ERROR_MISSING = "Could not locate token at %s"
TOKEN_ERROR_PERMISSIONS = (
    "Minimum required permissions: '%s'. Not available in token '%s' for account '%s'."
)
TOKEN_EXPIRED = (
    "Token has expired for account: '%s'. " + "Please re-configure and re-authenticate."
)


TOKEN_FILENAME = "{0}{1}.token"  # nosec
TOKEN_FILE_CORRUPTED = "corrupted"
TOKEN_FILE_EXPIRED = "expired"
TOKEN_FILE_MISSING = "missing"
TOKEN_FILE_OUTDATED = "outdated"
TOKEN_FILE_PERMISSIONS = "permissions"
TOKEN_INVALID = "The token you are trying to load is not valid anymore"


class CountryOptions(StrEnum):
    """Teams sensors enablement."""

    DEFAULT = "Default"
    CN21V = "21Vianet (China)"


MSAL_AUTHORITY = "msal_authority"
OAUTH_REDIRECT_URL = "auth_redirect_url"
OAUTH_SCOPE_PREFIX = "oauth_scope_prefix"
PERMISSION_PREFIX = "permission_prefix"
PROTOCOL_URL = "protocol_url"

COUNTRY_URLS = {
    CountryOptions.CN21V: {
        MSAL_AUTHORITY: "https://login.partner.microsoftonline.cn/common",
        OAUTH_REDIRECT_URL: "https://login.partner.microsoftonline.cn/common/oauth2/nativeclient",
        OAUTH_SCOPE_PREFIX: "https://microsoftgraph.chinacloudapi.cn/",
        PERMISSION_PREFIX: "https://microsoftgraph.chinacloudapi.cn/",
        PROTOCOL_URL: "https://microsoftgraph.chinacloudapi.cn/",
    },
    CountryOptions.DEFAULT: {
        OAUTH_REDIRECT_URL: "https://login.microsoftonline.com/common/oauth2/nativeclient",
        PERMISSION_PREFIX: "https://graph.microsoft.com/",
    },
}
