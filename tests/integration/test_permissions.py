# pylint: disable=unused-argument, line-too-long
"""Test permission handling."""

from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from requests_mock import Mocker

from ..helpers.mock_config_entry import MS365MockConfigEntry
from ..helpers.utils import build_token_file
from .const_integration import DOMAIN, FULL_INIT_ENTITY_NO
from .helpers_integration.mocks import MS365MOCKS

### Note that permissions code also supports Presence/Send which are not present in the calendar integration


async def test_base_permissions(
    hass: HomeAssistant,
    setup_base_integration,
    base_config_entry: MS365MockConfigEntry,
) -> None:
    """Test base permissions."""
    assert "Calendars.Read" in base_config_entry.runtime_data.permissions.permissions


@pytest.mark.parametrize(
    "base_config_entry",
    [{"shared_mailbox": "jane.doe@nomail.com"}],
    indirect=True,
)
@pytest.mark.parametrize("base_token", ["Calendars.Read.Shared"], indirect=True)
async def test_shared_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test shared permissions."""
    MS365MOCKS.shared_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO


@pytest.mark.parametrize(
    "base_config_entry",
    [{"shared_mailbox": "jane.doe@nomail.com", "enable_update": True}],
    indirect=True,
)
@pytest.mark.parametrize("base_token", ["Calendars.ReadWrite.Shared"], indirect=True)
async def test_update_shared_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test shared update permissions."""
    MS365MOCKS.shared_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO
    assert hass.services.has_service(DOMAIN, "create_calendar_event")
    assert hass.services.has_service(DOMAIN, "modify_calendar_event")
    assert hass.services.has_service(DOMAIN, "remove_calendar_event")
    assert hass.services.has_service(DOMAIN, "respond_calendar_event")


async def test_missing_permissions(
    tmp_path,
    hass: HomeAssistant,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
):
    """Test for missing permissions."""
    build_token_file(tmp_path, "")

    base_config_entry.add_to_hass(hass)
    with patch(
        "homeassistant.helpers.issue_registry.async_create_issue"
    ) as mock_async_create_issue:
        await hass.config_entries.async_setup(base_config_entry.entry_id)

    assert "Minimum required permissions: 'Calendars.Read'" in caplog.text
    assert mock_async_create_issue.called


@pytest.mark.parametrize("base_token", ["Calendars.ReadWrite"], indirect=True)
async def test_higher_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that higher permissions work."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO


@pytest.mark.parametrize("base_token", ["Calendars.Read.Shared"], indirect=True)
async def test_shared_higher_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that shared higher permissions work."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO


@pytest.mark.parametrize(
    "base_config_entry",
    [{"basic_calendar": True}],
    indirect=True,
)
async def test_basic_permissions(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test basic permissions."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO


@pytest.mark.parametrize(
    "base_config_entry",
    [{"shared_mailbox": "jane.doe@nomail.com"}],
    indirect=True,
)
async def test_shared_permissions_failure(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test shared permission missing."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    assert "Minimum required permissions: 'Calendars.Read.Shared'" in caplog.text


@pytest.mark.parametrize("base_config_entry", [{"groups": True}], indirect=True)
@pytest.mark.parametrize("base_token", ["Calendars.Read Group.Read.All"], indirect=True)
async def test_groups(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for group permissions."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO


@pytest.mark.parametrize(
    "base_config_entry", [{"groups": True, "enable_update": True}], indirect=True
)
@pytest.mark.parametrize(
    "base_token", ["Calendars.ReadWrite Group.ReadWrite.All"], indirect=True
)
async def test_update_groups(
    hass: HomeAssistant,
    requests_mock: Mocker,
    base_token,
    base_config_entry: MS365MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test for group update permissions."""
    MS365MOCKS.standard_mocks(requests_mock)
    base_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(base_config_entry.entry_id)
    await hass.async_block_till_done()

    entities = er.async_entries_for_config_entry(
        entity_registry, base_config_entry.entry_id
    )
    assert len(entities) == FULL_INIT_ENTITY_NO
