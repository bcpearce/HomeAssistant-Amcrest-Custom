"""Switches for Amcrest integration."""

from typing import Any

from homeassistant.components.camera import (
    DOMAIN as CAMERA_DOMAIN,
    SERVICE_DISABLE_MOTION as CAMERA_SERVICE_DISABLE_MOTION,
    SERVICE_ENABLE_MOTION as CAMERA_SERVICE_ENABLE_MOTION,
    SERVICE_TURN_OFF as CAMERA_SERVICE_TURN_OFF,
    SERVICE_TURN_ON as CAMERA_SERVICE_TURN_ON,
)
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import AmcrestConfigEntry, AmcrestDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Amcrest binary sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        [
            AmcrestPrivacyModeSwitch(coordinator),
            AmcrestMotionDetectionSwitch(coordinator),
        ]
    )


def _async_get_device_id(entity: Entity) -> str:
    if entity.device_info is None:
        raise ValueError("No device associated with entity")
    device_registry: dr.DeviceRegistry = dr.async_get(entity.hass)
    device_entry = device_registry.async_get_device(entity.device_info["identifiers"])
    if device_entry is None:
        raise RuntimeError("No device entry found for entity")
    return device_entry.id


class AmcrestPrivacyModeSwitch(CoordinatorEntity[AmcrestDataCoordinator], SwitchEntity):
    """Privacy Mode Switch. Implement Camera On/Off."""

    _attr_has_entity_name = True
    _attr_translation_key = "privacy_mode"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{coordinator.fixed_config.serial_number}-privacy_mode"
        self._attr_device_info: dr.DeviceInfo = coordinator.device_info
        self._attr_is_on = self.coordinator.amcrest_data.privacy_mode_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn privacy mode on (Camera Off)."""
        await self.hass.services.async_call(
            CAMERA_DOMAIN,
            CAMERA_SERVICE_TURN_OFF,
            target={ATTR_DEVICE_ID: _async_get_device_id(self)},
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off (Camera On)."""
        await self.hass.services.async_call(
            CAMERA_DOMAIN,
            CAMERA_SERVICE_TURN_ON,
            target={ATTR_DEVICE_ID: _async_get_device_id(self)},
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.coordinator.amcrest_data.privacy_mode_on
        self.async_write_ha_state()


class AmcrestMotionDetectionSwitch(
    CoordinatorEntity[AmcrestDataCoordinator], SwitchEntity
):
    """Privacy Mode Switch. Implement Camera On/Off."""

    _attr_has_entity_name = True
    _attr_translation_key = "enable_motion_detection"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = (
            f"{coordinator.fixed_config.serial_number}-enable_motion_detection"
        )
        self._attr_device_info = coordinator.device_info
        self._attr_is_on = coordinator.is_listening_for_events

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn privacy mode on (Camera Off)."""
        await self.hass.services.async_call(
            CAMERA_DOMAIN,
            CAMERA_SERVICE_ENABLE_MOTION,
            target={ATTR_DEVICE_ID: _async_get_device_id(self)},
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off (Camera On)."""
        await self.hass.services.async_call(
            CAMERA_DOMAIN,
            CAMERA_SERVICE_DISABLE_MOTION,
            target={ATTR_DEVICE_ID: _async_get_device_id(self)},
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.coordinator.is_listening_for_events
        self.async_write_ha_state()
