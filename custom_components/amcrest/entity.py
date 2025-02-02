"""Base Entity."""

from homeassistant.const import CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import MANUFACTURER
from .coordinator import AmcrestDataCoordinator


class AmcrestEntity(CoordinatorEntity[AmcrestDataCoordinator]):
    """Base entity for integration."""

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for any entity using this coordinator."""
        return DeviceInfo(
            identifiers=self.coordinator.identifiers,
            connections=self.coordinator.connections,
            configuration_url=self.coordinator.api.url,
            manufacturer=MANUFACTURER,
            sw_version=self.coordinator.fixed_config.software_version,
            name=self.coordinator.config_entry.data[CONF_NAME],
            serial_number=self.coordinator.fixed_config.serial_number,
            model=self.coordinator.fixed_config.device_type,
            hw_version=self.coordinator.fixed_config.hardware_version,
        )
