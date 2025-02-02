"""Support for Amcrest IP camera binary sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from amcrest_api.event import EventAction
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback

from .entity import AmcrestEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import AmcrestConfigEntry
    from .coordinator import AmcrestDataCoordinator


# pylint: disable=unused-argument
async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Amcrest binary sensors."""
    coordinator = entry.runtime_data

    async_add_entities([AmcrestVideoMotionSensor(coordinator)])


class AmcrestVideoMotionSensor(AmcrestEntity, BinarySensorEntity):
    """Binary sensor for Amcrest camera."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "motion_detected"

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{coordinator.fixed_config.serial_number}-motion_sensor"

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.is_listening_for_events:
            if self.coordinator.amcrest_data.last_video_motion_event is None:
                self._attr_is_on = False
            else:
                self._attr_is_on = (
                    self.coordinator.amcrest_data.last_video_motion_event.action
                    == EventAction.Start
                )
        else:
            # Unavailable if not listening
            self._attr_is_on = None
        self.async_write_ha_state()
