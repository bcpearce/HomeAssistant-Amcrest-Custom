"""Support for Amcrest IP cameras."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from amcrest_api.ptz import PtzBasicMove, PtzRelativeMove
import voluptuous as vol

from homeassistant.components.camera import Camera as CameraEntity, CameraEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)

from . import AmcrestConfigEntry
from .coordinator import AmcrestDataCoordinator

_LOGGER = logging.getLogger(__name__)

_PAN = "pan"
_PAN_DIRECTION = "pan_direction"
_TILT = "tilt"
_TILT_DIRECTION = "tilt_direction"
_ZOOM = "zoom"
_ZOOM_DIRECTION = "zoom_direction"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IP Camera from config entry."""
    camera = AmcrestCameraEntity(coordinator=entry.runtime_data)
    async_add_entities([camera])

    platform = async_get_current_platform()

    platform.async_register_entity_service(
        _PAN,
        vol.Schema({vol.Required(_PAN_DIRECTION): cv.string}, extra=vol.ALLOW_EXTRA),
        "async_handle_ptz",
    )
    platform.async_register_entity_service(
        _TILT,
        vol.Schema({vol.Required(_TILT_DIRECTION): cv.string}, extra=vol.ALLOW_EXTRA),
        "async_handle_ptz",
    )


class AmcrestCameraEntity(CameraEntity):
    """Amcrest IP camera entity."""

    _attr_supported_features = CameraEntityFeature.STREAM | CameraEntityFeature.ON_OFF
    _attr_is_on = True
    _attr_has_entity_name = True
    _attr_translation_key = "main_stream"
    _attr_can_pan = False
    _attr_can_tilt = False
    _attr_can_zoom = False

    def __init__(
        self,
        *,
        coordinator: AmcrestDataCoordinator,
    ) -> None:
        """Initialize the Amcrest camera entity."""
        super().__init__()
        self._coordinator = coordinator
        self._attr_unique_id = self._coordinator.fixed_config.serial_number
        self._attr_is_on = not self._coordinator.amcrest_data.privacy_mode_on
        self._attr_is_streaming = not self._coordinator.amcrest_data.privacy_mode_on
        self._attr_device_info = coordinator.device_info
        self._attr_can_pan = coordinator.fixed_config.ptz_capabilities.pan
        self._attr_can_tilt = coordinator.fixed_config.ptz_capabilities.tilt
        self._attr_can_zoom = coordinator.fixed_config.ptz_capabilities.zoom

    async def async_turn_on(self) -> None:
        """Disable 'Privacy Mode'. The Camera does not support remote On/Off, however the functionality of Privacy Mode is similar. It will disable the feed and point the camera down and into its own base."""
        await self._coordinator.api.async_set_privacy_mode_on(False)
        self._attr_is_on = True
        self._attr_is_streaming = True
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Enable 'Privacy Mode'. The Camera does not support remote On/Off, however the functionality of Privacy Mode is similar. It will disable the feed and point the camera down and into its own base."""
        await self._coordinator.api.async_set_privacy_mode_on(True)
        self._attr_is_on = False
        self._attr_is_streaming = False
        self.async_write_ha_state()

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection."""
        self._coordinator.async_enable_event_listener()

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection."""
        await self._coordinator.async_disable_event_listener()

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        if self._attr_is_on:
            return bytes(await self._coordinator.api.async_snapshot())
        return None

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        if self._attr_is_streaming:
            return str(self._coordinator.api.rtsp_url)
        return None

    async def async_handle_ptz(self, **kwargs: Any) -> None:
        """Handle PTZ service calls."""
        if kwargs.get("move_mode") == "relative":
            move = PtzRelativeMove()
            if (direction := kwargs.get(_PAN_DIRECTION)) is not None:
                move.horizontal = kwargs.get("distance", 0.0) * (
                    -1.0 if direction == "left" else 1.0
                )
            elif (direction := kwargs.get(_TILT_DIRECTION)) is not None:
                move.vertical = kwargs.get("distance", 0.0) * (
                    -1.0 if direction == "down" else 1.0
                )
            await self._coordinator.api.async_ptz_move_relative(move)
        elif (move_mode := kwargs.get("move_mode")) in ["continuous", "stop"]:
            pan_direction = kwargs.get(_PAN_DIRECTION)
            tilt_direction = kwargs.get(_TILT_DIRECTION)
            move = PtzBasicMove(pan_direction or tilt_direction)
            if move_mode == "continuous":
                if (speed := kwargs.get("speed")) is not None:
                    move.speed = speed
                seconds = kwargs.get("continuous_duration_seconds")
                duration = timedelta(seconds=seconds) if seconds is not None else None
                await self._coordinator.api.async_ptz_move(move, duration)
            elif move_mode == "stop":
                await self._coordinator.api.async_ptz_stop(move)
        await self._coordinator.async_request_refresh()
