"""Constants for MS365 testing."""

from pathlib import Path

CLIENT_ID = "1234"
CLIENT_SECRET = "5678"
TITLE = "mock"
ENTITY_NAME = "test"


TOKEN_PARAMS = "code=fake.code&state={0}&session_state=fakesessionstate"
TOKEN_URL_ASSERT = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/"
    + "authorize?response_type=code&client_id="
)

STORAGE_LOCATION = "storage"
TOKEN_LOCATION = "storage/tokens"

TEST_DATA_LOCATION = Path(__file__).parent.joinpath("data")
TEST_DATA_INTEGRATION_LOCATION = Path(__file__).parent.joinpath(
    "integration/data_integration"
)
