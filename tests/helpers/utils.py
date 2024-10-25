"""Utilities for MS365 testing."""

import json
import pathlib
import re
import shutil
import time
from datetime import datetime, timezone

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.ms365_calendar.integration.const_integration import (
    CONF_CALENDAR_LIST,
    CONF_HOURS_BACKWARD_TO_GET,
    CONF_HOURS_FORWARD_TO_GET,
    CONF_MAX_RESULTS,
    CONF_TRACK_NEW_CALENDAR,
    DOMAIN,
)

from .const import ENTITY_NAME, TOKEN_PARAMS, UPDATE_CALENDAR_LIST
from .mock_config_entry import MS365MockConfigEntry

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
    state = re.search(
        "state=(.*?)&", result["description_placeholders"]["auth_url"]
    ).group(1)

    return token_url + "?" + TOKEN_PARAMS.format(state)


def build_token_file(scope):
    """Build a token file."""
    token = _build_token(scope)
    token["expires_at"] = time.time() + TOKEN_TIME
    token["scope"] = token["scope"].split()
    filename = pathlib.Path(__file__).parent.joinpath(
        "../data/storage/tokens", f"{DOMAIN}_{ENTITY_NAME}.token"
    )

    with open(filename, "w", encoding="UTF8") as f:
        json.dump(token, f, ensure_ascii=False, indent=1)


def mock_call(
    requests_mock, urlname, datafile, unique=None, start=None, end=None, method="get"
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
    return (
        pathlib.Path(__file__)
        .parent.joinpath("../data/", filename)
        .read_text(encoding="utf8")
    )


def check_entity_state(
    hass,
    entity_name,
    entity_state,
    entity_attributes=None,
    data_length=None,
    subject=None,
):
    """Check entity state."""
    state = hass.states.get(entity_name)
    print("*************************** State")
    print(state.state)
    print(state.attributes["data"])
    assert state.state == entity_state
    if entity_attributes:
        # print("*************************** State Attributes")
        # print(state.attributes)
        assert state.attributes["data"] == entity_attributes
    if data_length is not None:
        assert len(state.attributes["data"]) == data_length
    if subject is not None:
        assert state.attributes["message"] == subject


def utcnow():
    """Get UTC Now."""
    return datetime.now(timezone.utc)


def yaml_setup(infile):
    """Setup a yaml file"""
    fromfile = pathlib.Path(__file__).parent.joinpath("../data/yaml/", f"{infile}.yaml")
    tofile = pathlib.Path(__file__).parent.joinpath(
        "../data/storage/ms365_calendars_test.yaml"
    )
    shutil.copy(fromfile, tofile)


def token_setup(infile):
    """Setup a yaml file"""
    fromfile = pathlib.Path(__file__).parent.joinpath(
        "../data/token/", f"{infile}.token"
    )
    tofile = pathlib.Path(__file__).parent.joinpath(
        "../data/storage/tokens/ms365_calendar_test.token"
    )
    shutil.copy(fromfile, tofile)


async def update_options(
    hass: HomeAssistant,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test the options flow"""

    result = await hass.config_entries.options.async_init(base_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_TRACK_NEW_CALENDAR: False,
            CONF_CALENDAR_LIST: UPDATE_CALENDAR_LIST,
        },
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Calendar1_Changed",
            CONF_HOURS_FORWARD_TO_GET: 48,
            CONF_HOURS_BACKWARD_TO_GET: -48,
            CONF_MAX_RESULTS: 5,
        },
    )
