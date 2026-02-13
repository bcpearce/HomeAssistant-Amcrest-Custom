"""Switches for Amcrest integration."""

from typing import Any

import homeassistant.helpers.device_registry as dr
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmcrestConfigEntry, AmcrestDataCoordinator
from .entity import AmcrestEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Amcrest switches."""
    coordinator = entry.runtime_data
    entities: list[Entity] = []
    if coordinator.fixed_config.smart_track_available:
        entities.append(AmcrestPtzSmartTrackSwitch(coordinator))
    if coordinator.fixed_config.privacy_mode_available:
        entities.append(AmcrestPrivacyModeSwitch(coordinator))
    async_add_entities(entities)


def _async_get_device_id(entity: Entity) -> str:
    if entity.device_info is None:
        raise ValueError("No device associated with entity")
    device_registry: dr.DeviceRegistry = dr.async_get(entity.hass)
    device_entry = device_registry.async_get_device(entity.device_info["identifiers"])
    if device_entry is None:
        raise RuntimeError("No device entry found for entity")
    return device_entry.id


class AmcrestPrivacyModeSwitch(AmcrestEntity, SwitchEntity):
    """Privacy Mode Switch. Implement Camera On/Off."""

    _attr_has_entity_name = True
    _attr_translation_key = "privacy_mode"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{coordinator.fixed_config.serial_number}-privacy_mode"
        self._attr_is_on = self.coordinator.amcrest_data.privacy_mode_on

    async def _handle_privacy_mode(self, is_on: bool) -> None:
        await self.coordinator.api.async_set_privacy_mode_on(is_on)
        await self.coordinator.async_refresh()
        # Note this is inverse to camera "on" state
        self._attr_is_on = is_on
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn privacy mode on (Camera Off)."""
        await self._handle_privacy_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off (Camera On)."""
        await self._handle_privacy_mode(False)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.coordinator.amcrest_data.privacy_mode_on
        self.async_write_ha_state()


class AmcrestPtzSmartTrackSwitch(AmcrestEntity, SwitchEntity):
    """Smart Track Switch. Automatically tracks detected motion."""

    _attr_has_entity_name = True
    _attr_translation_key = "smart_track"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"{coordinator.fixed_config.serial_number}-smart_track"
        self._attr_is_on = coordinator.amcrest_data.smart_track_on

    async def _handle_smart_track(self, turn_on: bool) -> None:
        await self.coordinator.api.async_set_smart_track_on(turn_on)
        self._attr_is_on = turn_on
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn smart tracking on."""
        await self._handle_smart_track(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn smart tracking off."""
        await self._handle_smart_track(False)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = self.coordinator.amcrest_data.smart_track_on
        self.async_write_ha_state()
