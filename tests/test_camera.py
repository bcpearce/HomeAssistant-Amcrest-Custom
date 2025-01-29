"""Test the camera entity."""

from unittest.mock import AsyncMock, patch

import pytest
from amcrest_api.const import StreamType
from homeassistant.components.camera import async_get_image, async_get_stream_source
from homeassistant.components.camera.const import DOMAIN as CAMERA_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amcrest.camera import AmcrestCameraEntity
from custom_components.amcrest.coordinator import AmcrestDataCoordinator

from .utils import setup_integration


@pytest.fixture(name="cameras_and_coordinator")
async def cameras_and_coordinator_fixture(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> tuple[er.RegistryEntry, er.RegistryEntry, AmcrestDataCoordinator]:
    """Get the cameras and coordinator associated with the mock config."""
    entry = await setup_integration(hass, mock_config_entry)
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    coordinator: AmcrestDataCoordinator = entry.runtime_data
    ent_reg = er.async_get(hass)
    main_stream = ent_reg.async_get("camera.amc_test_main_stream")
    sub_stream_1 = ent_reg.async_get("camera.amc_test_sub_stream_1")
    return main_stream, sub_stream_1, coordinator  # type: ignore


@pytest.mark.parametrize(
    "service_call,expected_called_with",
    [(SERVICE_TURN_ON, False), (SERVICE_TURN_OFF, True)],
)
async def test_turn_on_off(
    hass: HomeAssistant,
    cameras_and_coordinator: tuple[
        er.RegistryEntry,
        er.RegistryEntry,
        AmcrestDataCoordinator,
    ],
    service_call: str,
    expected_called_with: bool,
) -> None:
    """Test the camera can turn on with an event, and return a stream URL."""
    main_stream, _, coordinator = cameras_and_coordinator
    with patch.object(
        coordinator.api, "async_set_privacy_mode_on", new_callable=AsyncMock
    ) as mock_capture:
        await hass.services.async_call(
            CAMERA_DOMAIN,
            service_call,
            {ATTR_ENTITY_ID: main_stream.entity_id},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once_with(expected_called_with)


async def test_get_stream_and_image(
    hass: HomeAssistant,
    cameras_and_coordinator: tuple[
        AmcrestCameraEntity, AmcrestCameraEntity, AmcrestDataCoordinator
    ],
) -> None:
    """Test the stream is obtainable based on whether the image is on."""
    main_stream, sub_stream_1, coordinator = cameras_and_coordinator
    with patch.object(
        coordinator.api,
        "async_get_rtsp_url",
        new_callable=AsyncMock,
        return_value="rtsp://10.0.0.1:554/stream",
    ) as mock_capture:
        await async_get_stream_source(hass, main_stream.entity_id)
        mock_capture.assert_called_with(subtype=StreamType.MAIN)
        await async_get_stream_source(hass, sub_stream_1.entity_id)
        mock_capture.assert_called_with(subtype=StreamType.SUBSTREAM1)

    with patch.object(
        coordinator.api,
        "async_snapshot",
        new_callable=AsyncMock,
        return_value=b"\0" * 480 * 360,
    ) as mock_capture:
        await async_get_image(hass, main_stream.entity_id)
        mock_capture.assert_called_with(subtype=StreamType.MAIN)
        await async_get_image(hass, sub_stream_1.entity_id)
        mock_capture.assert_called_with(subtype=StreamType.SUBSTREAM1)
