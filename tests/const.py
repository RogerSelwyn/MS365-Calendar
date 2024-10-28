"""Constants for MS365 testing."""

import os
from pathlib import Path

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
TITLE = "mock"
ENTITY_NAME = "test"

# AUTH_URL = "https://its_a_fake_url"
# TOKEN_URL = "http://its_another_fake_url_with_a_code=12345"
TOKEN_PARAMS = "code=fake.code&state={0}&session_state=fakesessionstate"
TOKEN_URL_ASSERT = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/"
    + "authorize?response_type=code&client_id="
)

DATA_LOCATION = Path(__file__).parent.joinpath("data")
STORAGE_LOCATION = os.path.join(DATA_LOCATION, "storage")
TOKEN_LOCATION = os.path.join(DATA_LOCATION, "storage/tokens")
