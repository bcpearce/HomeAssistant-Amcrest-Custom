"""Test component initialization."""

from typing import Any
from unittest.mock import AsyncMock, patch

import homeassistant.helpers.entity_registry as er
import pytest
from amcrest_api.config import Config as AmcrestFixedConfig
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from zeroconf import ServiceInfo

from custom_components.amcrest import (
    SERVICE_PAN,
    SERVICE_PAN_DIRECTION,
    SERVICE_TILT,
)
from custom_components.amcrest.const import DOMAIN
from custom_components.amcrest.coordinator import AmcrestData, AmcrestDataCoordinator

from .utils import setup_integration


@pytest.fixture(
    name="parameterized_config_entry",
    params=["mock_config_entry", "mock_zeroconf_config_entry"],
)
def parameterized_config_entry_fixture(
    request: Any,
    mock_config_entry: MockConfigEntry,
    mock_zeroconf_config_entry: MockConfigEntry,
) -> MockConfigEntry | None:
    """Returns one of the config entry fixtures."""
    if request.param == "mock_config_entry":
        return mock_config_entry
    elif request.param == "mock_zeroconf_config_entry":
        return mock_zeroconf_config_entry
    pytest.fail("Not a valid config_entry fixture name")


async def test_load_and_unload_entry(
    hass: HomeAssistant,
    parameterized_config_entry: MockConfigEntry,
    mock_fixed_config: AmcrestFixedConfig,
    mock_discovery_info: ZeroconfServiceInfo,
) -> None:
    """Test setup of the integration."""
    with (
        patch(
            "custom_components.amcrest.coordinator.AmcrestDataCoordinator.async_get_fixed_config",
            new_callable=AsyncMock,
            return_value=mock_fixed_config,
        ),
        patch(
            "custom_components.amcrest.coordinator.AmcrestDataCoordinator.async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(),
        ),
        patch(
            "custom_components.amcrest.async_get_service_info",
            new_callable=AsyncMock,
            return_value=ServiceInfo(
                type_=mock_discovery_info.type,
                name=mock_discovery_info.name,
                addresses=mock_discovery_info.addresses,
                port=mock_discovery_info.port,
            ),
        ),
    ):
        entry = await setup_integration(hass, parameterized_config_entry)

        assert entry.state is ConfigEntryState.LOADED

        # all entries belong to the same device
        entity_registry = er.async_get(hass)
        entities = entity_registry.entities.get_entries_for_config_entry_id(
            entry.entry_id
        )
        device_id = entities[0].device_id
        assert all(entity.device_id == device_id for entity in entities)

        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()

        assert str(entry.state) == str(ConfigEntryState.NOT_LOADED)


async def test_ptz_service_call(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test setup of the integration."""
    entry = await setup_integration(hass, mock_config_entry)
    assert entry is not None

    coordinator: AmcrestDataCoordinator = entry.runtime_data
    device = dr.async_get(hass).async_get_device(coordinator.device_info["identifiers"])
    with patch.object(
        coordinator.api,
        "async_ptz_move_relative",
        new_callable=AsyncMock,
        return_value=AmcrestData(),
    ) as mock_capture:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PAN,
            service_data={
                ATTR_DEVICE_ID: device.id,
                SERVICE_PAN_DIRECTION: "left",
                "distance": 0.1,
                "move_mode": "relative",
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once()
    with patch.object(
        coordinator.api,
        "async_ptz_move",
        new_callable=AsyncMock,
        return_value=AmcrestData(),
    ) as mock_capture:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_TILT,
            service_data={
                ATTR_DEVICE_ID: device.id,
                SERVICE_PAN_DIRECTION: "up",
                "speed": 0.1,
                "continuous_duration_seconds": 0.5,
                "move_mode": "continuous",
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once()
