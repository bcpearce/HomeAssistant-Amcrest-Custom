"""Implements Light Element"""

from typing import Any

from amcrest_api.imaging import ConfigNo, Lighting
from homeassistant.components.light import LightEntity
from homeassistant.core import HomeAssistant
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

    coordinator = entry.runtime_data

    lighting = await coordinator.api.async_lighting_config

    entities_to_add = []

    for channel, configs in enumerate(lighting):
        for config_no, config in enumerate(configs):
            entities_to_add.append(
                AmcrestLight(coordinator, config, config_no, channel)
            )

    async_add_entities(entities_to_add)


class AmcrestLight(AmcrestEntity, LightEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "light"

    def __init__(
        self,
        coordinator: AmcrestDataCoordinator,
        lighting: Lighting,
        config_no: ConfigNo,
        channel: int = 1,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)
        self._lighting = lighting
        self._config_no = config_no
        self._channel = channel

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn device on."""
        await self.coordinator.api.async_set_lighting_config(
            self._config_no, self._lighting, index=0, channel=self._channel
        )
