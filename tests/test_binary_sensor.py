"""Test Binary Sensor Entities."""

import asyncio
from collections.abc import AsyncGenerator, Callable, Iterable
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from amcrest_api.event import (
    AudioMutationEvent,
    EventAction,
    EventBase,
    HeartbeatEvent,
    VideoMotionEvent,
)
from homeassistant.components.camera import (
    SERVICE_DISABLE_MOTION,
    SERVICE_ENABLE_MOTION,
)
from homeassistant.components.camera.const import DOMAIN as CAMERA_DOMAIN
from homeassistant.components.switch import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
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


def _make_mock_event_generator(
    events: Iterable[EventBase], *, interval: float = 5.0, wait_until: float = 30.0
) -> Callable[[], Any]:
    async def mock_event_generator(
        **kwargs: dict[Any, Any],
    ) -> AsyncGenerator[EventBase | None]:
        """Mock event generation."""
        try:
            yield HeartbeatEvent()
            await asyncio.sleep(interval)
            for event in events:
                yield event
                await asyncio.sleep(interval)
            while True:  # run till cancelled
                await asyncio.sleep(30.0)
                yield HeartbeatEvent()
        except asyncio.CancelledError:
            pass  # other errors should fail the test

    return mock_event_generator


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


UUT_MOTION_SENSOR = "binary_sensor.amc_test_motion_detected"
UUT_AUDIO_SENSOR = "binary_sensor.amc_test_audio_detected"
UUT_CAMERA = "camera.amc_test_main_stream"
UUT_MOTION_ENABLE_SWITCH = "switch.amc_test_enable_motion_detection"
UUT_AUDIO_ENABLE_SWITCH = "switch.amc_test_enable_audio_detection"

TEST_EVENT_DETECTION_DATA = [
    (
        [
            VideoMotionEvent(action=EventAction.Start, raw_data="{}"),
            VideoMotionEvent(action=EventAction.Stop, raw_data="{}"),
        ],
        (
            CAMERA_DOMAIN,
            SERVICE_ENABLE_MOTION,
        ),
        (
            CAMERA_DOMAIN,
            SERVICE_DISABLE_MOTION,
        ),
        UUT_CAMERA,
        UUT_MOTION_SENSOR,
    ),
    (
        [
            VideoMotionEvent(action=EventAction.Start, raw_data="{}"),
            VideoMotionEvent(action=EventAction.Stop, raw_data="{}"),
        ],
        (
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
        ),
        (SWITCH_DOMAIN, SERVICE_TURN_OFF),
        UUT_MOTION_ENABLE_SWITCH,
        UUT_MOTION_SENSOR,
    ),
    (
        [
            AudioMutationEvent(action=EventAction.Start, raw_data="null"),
            AudioMutationEvent(action=EventAction.Stop, raw_data="null"),
        ],
        (
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
        ),
        (SWITCH_DOMAIN, SERVICE_TURN_OFF),
        UUT_AUDIO_ENABLE_SWITCH,
        UUT_AUDIO_SENSOR,
    ),
]


@pytest.mark.parametrize(
    "mock_events,enable_event_args,disable_event_args,enable_entity_id,sensor_entity_id",
    TEST_EVENT_DETECTION_DATA,
    ids=[
        "Motion enabled by camera",
        "Motion enabled by switch",
        "Audio enabled by switch",
    ],
)
async def test_async_test_event_detection(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    mock_events: list[EventBase],
    enable_event_args: tuple[str, str],
    disable_event_args: tuple[str, str],
    enable_entity_id: str,
    sensor_entity_id: str,
) -> None:
    """Test binary sensor for motion detection."""

    entry = await setup_integration(hass, mock_config_entry)
    assert entry is not None
    coordinator: AmcrestDataCoordinator = entry.runtime_data
    coordinator.api.async_set_audio_detect_on = AsyncMock()

    TICK = 5.0
    # precondition, unknown state
    assert hass.states.is_state(sensor_entity_id, STATE_UNKNOWN)
    coordinator.api.async_listen_events = _make_mock_event_generator(
        mock_events, interval=TICK
    )
    await hass.services.async_call(
        enable_event_args[0],
        enable_event_args[1],
        target={ATTR_ENTITY_ID: enable_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert coordinator.is_listening_for_events
    assert hass.states.is_state(sensor_entity_id, STATE_OFF)

    # advance time, expect the event to fire for Video Motion Start
    freezer.tick(TICK + 0.01)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.is_listening_for_events
    assert hass.states.is_state(sensor_entity_id, STATE_ON)

    # advance time again, expect the event to fire for Video Motion Stop
    freezer.tick(TICK + 0.01)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert coordinator.is_listening_for_events
    assert hass.states.is_state(sensor_entity_id, STATE_OFF)

    # disable event generation
    await hass.services.async_call(
        disable_event_args[0],
        disable_event_args[1],
        target={ATTR_ENTITY_ID: enable_entity_id},
        blocking=True,
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    freezer.tick(DEFAULT_UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.is_state(sensor_entity_id, STATE_UNKNOWN)
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
    assert entry is not None
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
    TICK = 5.0
    freezer.tick(TICK + 0.01)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert not coordinator.is_listening_for_events
    coordinator.async_update_listeners()  # type: ignore
    assert hass.states.is_state(UUT_SENSOR, STATE_UNKNOWN)

    coordinator.api.async_listen_events = _make_mock_event_generator(
        [
            VideoMotionEvent(action=EventAction.Start, raw_data="{}"),
            VideoMotionEvent(action=EventAction.Stop, raw_data="{}"),
        ],
        interval=TICK,
    )
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
