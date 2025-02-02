"""Sensors for Amcrest Camera."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import AmcrestConfigEntry
from .coordinator import AmcrestDataCoordinator
from .entity import AmcrestEntity


@dataclass(frozen=True, kw_only=True)
class AmcrestSensorEntityDescription(SensorEntityDescription):  # type: ignore
    """Describes the Amcrest sensor entity."""

    exists_fn: Callable[[AmcrestDataCoordinator], bool] = lambda _: True
    value_fn: Callable[[AmcrestDataCoordinator], StateType]


DESCRIPTIONS: tuple[AmcrestSensorEntityDescription, ...] = (
    AmcrestSensorEntityDescription(
        key="position_pan",
        translation_key="position_pan",
        icon="mdi:angle-acute",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="degrees",
        suggested_display_precision=1,
        exists_fn=lambda coordinator: coordinator.fixed_config.ptz_capabilities.pan,
        value_fn=lambda coordinator: coordinator.amcrest_data.ptz_status.position_pan,
    ),
    AmcrestSensorEntityDescription(
        key="position_tilt",
        translation_key="position_tilt",
        icon="mdi:angle-acute",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="degrees",
        suggested_display_precision=1,
        exists_fn=lambda coordinator: coordinator.fixed_config.ptz_capabilities.tilt,
        value_fn=lambda coordinator: coordinator.amcrest_data.ptz_status.position_tilt,
    ),
    AmcrestSensorEntityDescription(
        key="position_zoom",
        translation_key="position_zoom",
        icon="mdi:magnify",
        state_class=SensorStateClass.MEASUREMENT,
        # unitless
        suggested_display_precision=1,
        exists_fn=lambda coordinator: coordinator.fixed_config.ptz_capabilities.zoom,
        value_fn=lambda coordinator: coordinator.amcrest_data.ptz_status.position_zoom,
    ),
    AmcrestSensorEntityDescription(
        key="url",
        translation_key="url",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda coordinator: str(coordinator.api.url),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Amcrest binary sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        AmcrestSensor(coordinator=coordinator, description=description)
        for description in DESCRIPTIONS
        if description.exists_fn(coordinator)
    )


class AmcrestSensor(AmcrestEntity, SensorEntity):
    """Amcrest PTZ position sensor."""

    _attr_has_entity_name = True
    entity_description: AmcrestSensorEntityDescription

    def __init__(
        self,
        coordinator: AmcrestDataCoordinator,
        description: AmcrestSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.fixed_config.serial_number}-f{self.entity_description.key}"
        )

    @property
    def native_value(self) -> StateType:
        """Native sensor value."""
        return self.entity_description.value_fn(self.coordinator)
