"""Work-location sensor entities."""

from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from ..classes.config_entry import MS365ConfigEntry
from ..classes.entity import MS365Entity
from ..const import CONF_ENTITY_NAME
from .const_integration import (
    CONF_CAL_ID,
    CONF_DEVICE_ID,
    CONF_ENTITY,
    WORK_LOCATION_CAL_ID,
)
from .work_location_integration import (
    get_day_location_state,
    get_day_work_location_types,
)


async def async_integration_setup_entry(
    hass,  # pylint: disable=unused-argument
    entry: MS365ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MS365 sensor platform."""
    entities = []
    for key in entry.runtime_data.sensors:
        if key[CONF_CAL_ID] != WORK_LOCATION_CAL_ID:
            continue

        cal_id = key[CONF_CAL_ID]
        entity = key[CONF_ENTITY]
        device_id = entity[CONF_DEVICE_ID]
        for coordinator in entry.runtime_data.coordinator:
            if f"{device_id}_{cal_id}" != coordinator.name:
                continue

            entity_id = key[CONF_ENTITY_ID].split(".", 1)[1]
            unique_base = (
                f"{coordinator.sync.calendar_id}_{entry.data[CONF_ENTITY_NAME]}_{device_id}"
            )
            entities.append(
                MS365WorkLocationDaySensor(
                    coordinator,
                    entry,
                    "Work Location Today",
                    f"sensor.{entity_id}_today_location",
                    f"{unique_base}_today_location",
                    0,
                )
            )
            entities.append(
                MS365WorkLocationDaySensor(
                    coordinator,
                    entry,
                    "Work Location Tomorrow",
                    f"sensor.{entity_id}_tomorrow_location",
                    f"{unique_base}_tomorrow_location",
                    1,
                )
            )
            break

    if entities:
        async_add_entities(entities, False)


class MS365WorkLocationDaySensor(MS365Entity, SensorEntity):
    """Current work-location state for a given day offset."""

    _attr_icon = "mdi:map-marker-account"

    def __init__(
        self,
        coordinator,
        entry: MS365ConfigEntry,
        name: str,
        entity_id: str,
        unique_id: str,
        day_offset: int,
    ) -> None:
        """Initialise the Work Location day sensor."""
        super().__init__(coordinator, entry, name, entity_id, unique_id)
        self.entity_id = entity_id
        self._day_offset = day_offset

    @property
    def native_value(self) -> str:
        """Sensor value."""
        if self.coordinator.data is None:
            return "unknown"
        target = dt_util.now().date() + timedelta(days=self._day_offset)
        range_start = dt_util.as_utc(
            dt_util.start_of_local_day(
                dt_util.dt.datetime.combine(target, dt_util.dt.time.min)
            )
        )
        range_end = range_start + timedelta(days=1)
        events = self.coordinator.data.overlapping(range_start, range_end)
        location_types = get_day_work_location_types(events, target)
        return get_day_location_state(location_types)
