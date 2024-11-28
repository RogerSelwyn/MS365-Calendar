"""Utilities for MS365 testing."""

import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from ..const import (
    ENTITY_NAME,
    TEST_DATA_INTEGRATION_LOCATION,
    TEST_DATA_LOCATION,
    TOKEN_LOCATION,
    TOKEN_PARAMS,
)
from ..integration.const_integration import DOMAIN

TOKEN_TIME = 5000


def mock_token(requests_mock, scope):
    """Mock up the token response based on scope."""
    token = json.dumps(_build_token(scope))
    requests_mock.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        text=token,
    )


def _build_token(scope):
    """Build a token"""
    return {
        "token_type": "Bearer",
        "scope": f"{scope} User.Read profile openid email",
        "expires_in": TOKEN_TIME,
        "ext_expires_in": TOKEN_TIME,
        "access_token": "fakeaccesstoken",
        "refresh_token": "fakerefreshtoken",
    }


def build_token_url(result, token_url):
    """Build the correct token url"""
    state = re.search("state=(.*?)&", result["description_placeholders"]["auth_url"])[1]

    return f"{token_url}?{TOKEN_PARAMS.format(state)}"


def build_token_file(tmp_path, scope):
    """Build a token file."""
    token = _build_token(scope)
    token["expires_at"] = time.time() + TOKEN_TIME
    token["scope"] = token["scope"].split()
    filename = tmp_path / TOKEN_LOCATION / f"{DOMAIN}_{ENTITY_NAME}.token"

    with open(filename, "w", encoding="UTF8") as f:
        json.dump(token, f, ensure_ascii=False, indent=1)


def mock_call(
    requests_mock,
    urlname,
    datafile,
    unique=None,
    start=None,
    end=None,
    method="get",
):
    """Mock a call"""
    data = load_json(f"O365/{datafile}.json")
    if start:
        data = data.replace("2020-01-01", start).replace("2020-01-02", end)

    url = urlname.value
    if unique:
        url = f"{url}/{unique}"
    if method == "get":
        requests_mock.get(
            url,
            text=data,
        )
    elif method == "post":
        requests_mock.post(
            url,
            text=data,
        )


def load_json(filename):
    """Load a json file as string."""
    filepath = TEST_DATA_INTEGRATION_LOCATION / filename
    return Path(filepath).read_text(encoding="utf8")


def check_entity_state(
    hass,
    entity_name,
    entity_state,
    entity_attributes=None,
    data_length=None,
    attributes=None,
):
    """Check entity state."""
    state = hass.states.get(entity_name)
    print(state)
    assert state.state == entity_state
    if entity_attributes:
        print("*************************** State Attributes")
        print(state.attributes)
        if "data" in state.attributes:
            assert state.attributes["data"] == entity_attributes
        else:
            assert state.attributes == entity_attributes
    if data_length is not None:
        assert len(state.attributes["data"]) == data_length

    if attributes is not None:
        for key, value in attributes.items():
            assert state.attributes.get(key, None) == value


def utcnow():
    """Get UTC Now."""
    return datetime.now(timezone.utc)


def token_setup(tmp_path, infile):
    """Setup a token file"""
    fromfile = TEST_DATA_LOCATION / f"token/{infile}.token"
    tofile = tmp_path / TOKEN_LOCATION / f"{DOMAIN}_test.token"
    shutil.copy(fromfile, tofile)


def get_schema_default(schema, key_name):
    """Iterate schema to find a key."""
    for schema_key in schema:
        if schema_key == key_name:
            try:
                return schema_key.default()
            except TypeError:
                return None
    raise KeyError(f"{key_name} not found in schema")
