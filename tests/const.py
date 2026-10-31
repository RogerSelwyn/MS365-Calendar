"""Constants for MS365 testing."""

from copy import deepcopy
from pathlib import Path

from .integration.const_integration import BASE_CONFIG_ENTRY_INTEGRATION, MIGRATION_CONFIG_ENTRY_INTEGRATION

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
ENTITY_NAME = "test"

LEGACY_TOKEN = {
    "access_token": "fakelegacytoken",
}

TENANT_OPTIONS = {"api_options": {"country": "Default", "tenant_id": ""}}

TOKEN_PARAMS = "code=fake.code&state={0}&session_state=fakesessionstate"
TOKEN_URL_ASSERT = "https://login.microsoftonline.com/common/oauth2/v2.0/" + "authorize?client_id="
TOKEN_URL_CN21V_ASSERT = "https://login.partner.microsoftonline.cn/common/oauth2/v2.0/authorize?client_id="
STORAGE_LOCATION = "storage"
TOKEN_LOCATION = "storage/tokens"

TEST_DATA_LOCATION = Path(__file__).parent.joinpath("data")
TEST_DATA_INTEGRATION_LOCATION = Path(__file__).parent.joinpath("integration/data_integration")


BASE_CONFIG_ENTRY = {
    "entity_name": ENTITY_NAME,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "alt_auth_method": False,
    "api_options": {"country": "Default"},
} | BASE_CONFIG_ENTRY_INTEGRATION

ALT_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
ALT_CONFIG_ENTRY["alt_auth_method"] = True
COUNTRY_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
COUNTRY_CONFIG_ENTRY["api_options"]["country"] = "21Vianet (China)"
ENV_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
ENV_CONFIG_ENTRY["environment_secret"] = True
RECONFIGURE_CONFIG_ENTRY = deepcopy(BASE_CONFIG_ENTRY)
del RECONFIGURE_CONFIG_ENTRY["entity_name"]

MIGRATION_CONFIG_ENTRY = MIGRATION_CONFIG_ENTRY_INTEGRATION
MIGRATION_CONFIG_ENTRY["data"] = BASE_CONFIG_ENTRY
