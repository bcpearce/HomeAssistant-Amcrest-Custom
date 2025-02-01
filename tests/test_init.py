"""Test component initialization."""

from typing import Any
from unittest.mock import AsyncMock, patch

import homeassistant.helpers.entity_registry as er
import pytest
from amcrest_api.config import Config as AmcrestFixedConfig
from amcrest_api.ptz import PtzPresetData
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from zeroconf import ServiceInfo

from custom_components.amcrest import (
    SERIVCE_TILT_DIRECTION,
    SERVICE_CLEAR_PTZ_PRESET,
    SERVICE_PAN,
    SERVICE_PAN_DIRECTION,
    SERVICE_PRESET_ID,
    SERVICE_PRESET_NAME,
    SERVICE_TILT,
    SERVICE_UPDATE_PTZ_PRESET,
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
    """Test PTZ service call."""
    entry = await setup_integration(hass, mock_config_entry)
    assert entry is not None

    coordinator: AmcrestDataCoordinator = entry.runtime_data
    device = dr.async_get(hass).async_get_device(coordinator.identifiers)
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
                SERIVCE_TILT_DIRECTION: "up",
                "speed": 0.1,
                "continuous_duration_seconds": 0.5,
                "move_mode": "continuous",
            },
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once()


async def test_ptz_preset_name_service_call(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test setting/naming of a PTZ preset."""
    entry = await setup_integration(hass, mock_config_entry)
    assert entry is not None

    coordinator: AmcrestDataCoordinator = entry.runtime_data
    device = dr.async_get(hass).async_get_device(coordinator.identifiers)

    preset_to_set = PtzPresetData(1, "TestPreset")
    with (
        patch.object(
            coordinator.api, "async_set_ptz_preset", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator,
            "async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(ptz_presets=[preset_to_set]),
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UPDATE_PTZ_PRESET,
            service_data={
                ATTR_DEVICE_ID: device.id,
                SERVICE_PRESET_NAME: preset_to_set.name,
                SERVICE_PRESET_ID: preset_to_set.index,
            },
            blocking=True,
        )
        # necessary to guarantee updates, refresh can be batched
        freezer.tick(60.0)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        mock_capture.assert_called_once_with(preset_to_set)

        assert preset_to_set in coordinator.amcrest_data.ptz_presets

    with (
        patch.object(
            coordinator.api, "async_clear_ptz_preset", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator,
            "async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(ptz_presets=[]),
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEAR_PTZ_PRESET,
            service_data={
                ATTR_DEVICE_ID: device.id,
                SERVICE_PRESET_ID: preset_to_set.index,
            },
            blocking=True,
        )
        # necessary to guarantee updates, refresh can be batched
        freezer.tick(60.0)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        mock_capture.assert_called_once_with(preset_to_set.index)

        assert preset_to_set not in coordinator.amcrest_data.ptz_presets
