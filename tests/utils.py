"""Utils to assist testing."""

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from tests.const import MOCK_DATA_UPDATE, MOCK_FIXED_CONFIG


async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> ConfigEntry | None:
    """Fixture for setting up the component."""
    config_entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.amcrest.coordinator.AmcrestDataCoordinator.async_get_fixed_config",
            new_callable=AsyncMock,
            return_value=MOCK_FIXED_CONFIG,
        ),
        patch(
            "custom_components.amcrest.coordinator.AmcrestDataCoordinator.async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=MOCK_DATA_UPDATE,
        ),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
    return hass.config_entries.async_get_entry(config_entry.entry_id)
