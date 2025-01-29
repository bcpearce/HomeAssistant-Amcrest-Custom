"""Test Select entities."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from homeassistant.components.camera.const import CameraState
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amcrest.data import AmcrestData

from .utils import setup_integration

if TYPE_CHECKING:
    from custom_components.amcrest.coordinator import AmcrestDataCoordinator


async def test_switch_privacy_mode(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test switching privacy mode (camera on/off)."""

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    UUT_SWITCH = "switch.amc_test_privacy_mode"
    UUT_MAIN_STREAM = "camera.amc_test_main_stream"
    UUT_SUB_STREAM_1 = "camera.amc_test_sub_stream_1"

    with (
        patch.object(
            coordinator.api, "async_set_privacy_mode_on", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator,
            "async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(privacy_mode_on=True),
        ),
    ):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            target={ATTR_ENTITY_ID: UUT_SWITCH},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once_with(True)

    # related camera entities should now be "off"
    assert hass.states.is_state(UUT_MAIN_STREAM, CameraState.IDLE)
    assert hass.states.is_state(UUT_SUB_STREAM_1, CameraState.IDLE)
    assert hass.states.is_state(UUT_SWITCH, STATE_ON)

    with (
        patch.object(
            coordinator.api, "async_set_privacy_mode_on", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator,
            "async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(privacy_mode_on=False),
        ),
    ):
        # now turn it off
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            target={ATTR_ENTITY_ID: UUT_SWITCH},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_with(False)

    assert hass.states.is_state(UUT_MAIN_STREAM, CameraState.STREAMING)
    assert hass.states.is_state(UUT_SUB_STREAM_1, CameraState.STREAMING)
    assert hass.states.is_state(UUT_SWITCH, STATE_OFF)

    await hass.async_block_till_done()


async def test_switch_smart_track(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test switching smart track on/off."""

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    UUT_SWITCH = "switch.amc_test_smart_tracking"

    with (
        patch.object(
            coordinator.api, "async_set_smart_track_on", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator,
            "async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(smart_track_on=False),
        ),
    ):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            target={ATTR_ENTITY_ID: UUT_SWITCH},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_with(True)
        assert hass.states.is_state(UUT_SWITCH, STATE_ON)

    with (
        patch.object(
            coordinator.api, "async_set_smart_track_on", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator,
            "async_poll_endpoints",
            new_callable=AsyncMock,
            return_value=AmcrestData(smart_track_on=False),
        ),
    ):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            target={ATTR_ENTITY_ID: UUT_SWITCH},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_with(False)
        assert hass.states.is_state(UUT_SWITCH, STATE_OFF)
