"""Select entities for Amcrest."""

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmcrestConfigEntry
from .coordinator import AmcrestDataCoordinator
from .entity import AmcrestEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IP Camera from config entry."""

    if entry.runtime_data.fixed_config.ptz_capabilities.preset:
        async_add_entities([PtzPresetSelectEntity(coordinator=entry.runtime_data)])


class PtzPresetSelectEntity(AmcrestEntity, SelectEntity):
    """Selector for PTZ presets."""

    _attr_has_entity_name = True
    _attr_translation_key = "ptz_preset"

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)
        self._attr_options = self._attr_options = [
            preset.name for preset in self.coordinator.amcrest_data.ptz_presets
        ]
        self._attr_current_option = None
        self._attr_unique_id = coordinator.fixed_config.serial_number

    async def async_select_option(self, option: str) -> None:
        """Select preset by name."""
        preset = next(
            preset
            for preset in self.coordinator.amcrest_data.ptz_presets
            if preset.name == option
        )
        self._attr_current_option = preset.name
        await self.coordinator.api.async_ptz_move_to_preset(preset.index)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_options = [
            preset.name for preset in self.coordinator.amcrest_data.ptz_presets
        ]
        self.async_write_ha_state()
