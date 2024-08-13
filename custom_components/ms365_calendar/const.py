"""Constants."""

ATTR_DATA = "data"
ATTR_ERROR = "error"
ATTR_STATE = "state"

AUTH_CALLBACK_NAME = "api:ms365"
AUTH_CALLBACK_PATH_ALT = "/api/ms365"
AUTH_CALLBACK_PATH_DEFAULT = (
    "https://login.microsoftonline.com/common/oauth2/nativeclient"
)

CONF_ENTITY_NAME = "entity_name"
CONF_ALT_AUTH_METHOD = "alt_auth_method"
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

PERM_OFFLINE_ACCESS = "offline_access"
PERM_USER_READ = "User.Read"
PERM_SHARED = ".Shared"


TOKEN_FILENAME = "{0}{1}.token"  # nosec
TOKEN_FILE_CORRUPTED = "corrupted"
TOKEN_FILE_MISSING = "missing"
TOKEN_FILE_PERMISSIONS = "permissions"
