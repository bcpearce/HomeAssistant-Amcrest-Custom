"""Test Select entities."""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from amcrest_api.imaging import (
    ConfigNo,
    VideoDayNight,
    VideoDayNightType,
    VideoImageControl,
    VideoMode,
    VideoSensitivity,
)
from homeassistant.components.select.const import DOMAIN as SELECT_DOMAIN
from homeassistant.components.select.const import SERVICE_SELECT_OPTION
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amcrest.const import RotationOption

from .utils import setup_integration

if TYPE_CHECKING:
    from custom_components.amcrest.coordinator import AmcrestDataCoordinator


async def test_async_select_ptz_preset_option(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test selecting an option for PTZ."""

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    with patch.object(
        coordinator.api, "async_ptz_move_to_preset", new_callable=AsyncMock
    ) as mock_capture:
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            service_data={"option": "Preset1"},
            target={"entity_id": "select.amc_test_ptz_preset"},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once()


async def test_async_select_video_image_control_option(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test selecting an option for Video Image Control."""

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    with patch.object(
        coordinator.api, "async_set_video_image_control", new_callable=AsyncMock
    ) as mock_capture:
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            service_data={"option": str(RotationOption.FLIP_180)},
            target={"entity_id": "select.amc_test_video_image_control"},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once_with(VideoImageControl(flip=True))


@pytest.mark.skip("uses a socket")
async def test_async_select_video_input_day_night(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test selecting an option for Video Image Control."""

    entry = await setup_integration(hass, mock_config_entry)
    coordinator: AmcrestDataCoordinator = entry.runtime_data

    vdn_from = VideoDayNight(
        delay_seconds=2,
        sensitivity=VideoSensitivity.MEDIUM,
        mode=VideoMode.BLACK_WHITE,
        type=VideoDayNightType.MECHANISM,
    )
    vdn_to = VideoDayNight(
        delay_seconds=2,
        sensitivity=VideoSensitivity.MEDIUM,
        mode=VideoMode.COLOR,
        type=VideoDayNightType.MECHANISM,
    )

    with (
        patch.object(
            coordinator.api, "async_set_video_in_day_night", new_callable=AsyncMock
        ) as mock_capture,
        patch.object(
            coordinator.api,
            "async_get_video_in_day_night",
            new_callable=AsyncMock,
            return_value=vdn_from,
        ),
    ):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            service_data={"option": str(VideoMode.COLOR)},
            target={"entity_id": "select.amc_test_video_input_day_night_day_profile"},
            blocking=True,
        )
        await hass.async_block_till_done()
        mock_capture.assert_called_once_with(vdn_to, config_no=ConfigNo.DAY, channel=1)
