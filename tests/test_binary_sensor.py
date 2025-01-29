"""Test Binary Sensor Entities."""

import asyncio
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

from amcrest_api.event import EventAction, EventBase, HeartbeatEvent, VideoMotionEvent
from homeassistant.components.camera import (
    SERVICE_DISABLE_MOTION,
    SERVICE_ENABLE_MOTION,
)
from homeassistant.components.camera.const import DOMAIN as CAMERA_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.amcrest.coordinator import DEFAULT_UPDATE_INTERVAL
from custom_components.amcrest.data import AmcrestData

from .utils import setup_integration

if TYPE_CHECKING:
    from custom_components.amcrest.coordinator import AmcrestDataCoordinator

import builtins

from freezegun.api import FrozenDateTimeFactory


async def mock_event_generator(
    **kwargs: dict[Any, Any],
) -> AsyncGenerator[EventBase | None]:
    """Mock event generation."""
    try:
        yield HeartbeatEvent()
        await asyncio.sleep(5.0)
        yield VideoMotionEvent(action=EventAction.Start, raw_data="{}")
        await asyncio.sleep(5.0)
        yield VideoMotionEvent(action=EventAction.Stop, raw_data="{}")
        while True:  # run till cancelled
            await asyncio.sleep(30.0)
            yield HeartbeatEvent()
    except asyncio.CancelledError:
        pass  # other errors should fail the test


async def mock_error_event_generator(
    **kwargs: dict[Any, Any],
) -> AsyncGenerator[EventBase | None]:
    """Mock event generation."""
    try:
        yield HeartbeatEvent()
        await asyncio.sleep(5.0)
        raise builtins.TimeoutError()
    except asyncio.CancelledError:
        pass  # other errors should fail the test


async def test_async_test_motion_detected(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test binary sensor for motion detection."""

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    UUT_SENSOR = "binary_sensor.amc_test_motion_detected"
    UUT_CAMERA = "camera.amc_test_main_stream"
    # precondition, unknown state
    assert hass.states.is_state(UUT_SENSOR, STATE_UNKNOWN)

    coordinator.api.async_listen_events = mock_event_generator

    await hass.services.async_call(
        CAMERA_DOMAIN,
        SERVICE_ENABLE_MOTION,
        target={ATTR_ENTITY_ID: UUT_CAMERA},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert coordinator.is_listening_for_events
    assert hass.states.is_state(UUT_SENSOR, STATE_OFF)

    # advance time, expect the event to fire for Video Motion Start
    freezer.tick(5.01)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.is_listening_for_events
    assert hass.states.is_state(UUT_SENSOR, STATE_ON)

    # advance time again, expect the event to fire for Video Motion Stop
    freezer.tick(5.01)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.is_listening_for_events
    assert hass.states.is_state(UUT_SENSOR, STATE_OFF)

    # disable event generation
    await hass.services.async_call(
        CAMERA_DOMAIN,
        SERVICE_DISABLE_MOTION,
        target={ATTR_ENTITY_ID: UUT_CAMERA},
        blocking=True,
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    freezer.tick(DEFAULT_UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.is_state(UUT_SENSOR, STATE_UNKNOWN)
    assert not coordinator.is_listening_for_events


async def test_restore_motion_detection(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """
    Test motion detection restoration.

    On an error, the listener will go down until the next polling operation.
    At that point, if the coordinator observes that the loop failed without
    an explicit shutdown, it will be restored.
    """

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    UUT_SENSOR = "binary_sensor.amc_test_motion_detected"
    UUT_CAMERA = "camera.amc_test_main_stream"
    # precondition, unknown state
    assert hass.states.is_state(UUT_SENSOR, STATE_UNKNOWN)

    coordinator.api.async_listen_events = mock_error_event_generator

    await hass.services.async_call(
        CAMERA_DOMAIN,
        SERVICE_ENABLE_MOTION,
        target={ATTR_ENTITY_ID: UUT_CAMERA},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert coordinator.is_listening_for_events
    assert hass.states.is_state(UUT_SENSOR, STATE_OFF)

    # advance time, expect the exception to be raised, and the sensor to be unavailable
    freezer.tick(5.01)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert not coordinator.is_listening_for_events
    coordinator.async_update_listeners()  # type: ignore
    assert hass.states.is_state(UUT_SENSOR, STATE_UNKNOWN)

    coordinator.api.async_listen_events = mock_event_generator
    with patch(
        "custom_components.amcrest.coordinator.AmcrestDataCoordinator.async_poll_endpoints",
        new_callable=AsyncMock,
        return_value=AmcrestData(),
    ):
        freezer.tick(DEFAULT_UPDATE_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert coordinator.is_listening_for_events
    assert hass.states.is_state(UUT_SENSOR, STATE_OFF)
