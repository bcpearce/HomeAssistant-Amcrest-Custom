"""Sensors for Amcrest Camera."""

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmcrestConfigEntry
from .coordinator import AmcrestDataCoordinator
from .entity import AmcrestEntity

DESCRIPTIONS = {
    "position_pan": SensorEntityDescription(
        key="position_pan",
        name="position_pan",
        translation_key="position_pan",
        icon="mdi:angle-acute",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="degrees",
        suggested_display_precision=1,
    ),
    "position_tilt": SensorEntityDescription(
        key="position_tilt",
        name="position_tilt",
        translation_key="position_tilt",
        icon="mdi:angle-acute",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="degrees",
        suggested_display_precision=1,
    ),
    "position_zoom": SensorEntityDescription(
        key="position_zoom",
        name="position_zoom",
        translation_key="position_zoom",
        icon="mdi:magnify",
        state_class=SensorStateClass.MEASUREMENT,
        # unitless
        suggested_display_precision=1,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Amcrest binary sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        [AmcrestPtzSensor(coordinator, desc) for desc in DESCRIPTIONS.values()]
    )


class AmcrestPtzSensor(AmcrestEntity, SensorEntity):
    """Amcrest PTZ position sensor."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: AmcrestDataCoordinator, description: SensorEntityDescription
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.fixed_config.serial_number}-f{self.entity_description.key}"
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        if (ptz_status := self.coordinator.amcrest_data.ptz_status) is not None:
            self._attr_native_value = getattr(ptz_status, self.entity_description.key)
        else:
            self._attr_native_value = None
        self.async_write_ha_state()
