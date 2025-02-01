"""Support for Amcrest IP cameras."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from amcrest_api.const import StreamType
from homeassistant.components.camera import Camera as CameraEntity
from homeassistant.components.camera import CameraEntityFeature
from homeassistant.core import callback
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity

from .entity import AmcrestEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback,
    )

    from . import AmcrestConfigEntry
    from .coordinator import AmcrestDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # pylint: disable=unused-argument
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IP Camera from config entry."""
    coordinator: AmcrestDataCoordinator = entry.runtime_data
    cameras = [AmcrestCameraEntity(coordinator=coordinator)]
    # set up subfeeds
    for i in range(1, coordinator.fixed_config.max_extra_stream + 1):
        cameras.append(
            AmcrestCameraEntity(coordinator=coordinator, stream_type=StreamType(i))
        )
    async_add_entities(cameras)


@dataclass(kw_only=True)
class AmcrestCameraExtraStoredData(ExtraStoredData):
    """Additional data for entity restoration."""

    motion_detection_enabled: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the extra data."""
        return {"motion_detection_enabled": self.motion_detection_enabled}


class AmcrestCameraEntity(CameraEntity, RestoreEntity, AmcrestEntity):
    """Amcrest IP camera entity."""

    _attr_is_on = True
    _attr_has_entity_name = True
    _attr_can_pan = False
    _attr_can_tilt = False
    _attr_can_zoom = False
    coordinator: AmcrestDataCoordinator | None = None  # type: ignore

    def __init__(
        self,
        *,
        coordinator: AmcrestDataCoordinator,
        stream_type: StreamType = StreamType.MAIN,
    ) -> None:
        """Initialize the Amcrest camera entity."""
        super().__init__()
        super(AmcrestEntity, self).__init__(coordinator=coordinator)
        self._attr_is_on = not self.coordinator.amcrest_data.privacy_mode_on
        self._attr_is_streaming = not self.coordinator.amcrest_data.privacy_mode_on
        self._attr_can_pan = coordinator.fixed_config.ptz_capabilities.pan
        self._attr_can_tilt = coordinator.fixed_config.ptz_capabilities.tilt
        self._attr_can_zoom = coordinator.fixed_config.ptz_capabilities.zoom
        self._attr_supported_features = (
            CameraEntityFeature.STREAM | CameraEntityFeature.ON_OFF
        )
        self._stream_type = stream_type
        self._attr_unique_id = (
            f"{self.coordinator.fixed_config.serial_number}-{self._stream_type}"
        )
        if stream_type == StreamType.MAIN:
            self._attr_translation_key = "main_stream"
        elif stream_type == StreamType.SUBSTREAM1:
            self._attr_translation_key = "sub_stream_1"
        elif stream_type == StreamType.SUBSTREAM2:
            self._attr_translation_key = "sub_stream_2"
        else:
            self._attr_translation_key = "unknown_stream"

    @property
    def extra_restore_state_data(self) -> ExtraStoredData | None:
        """Return motion detection state."""
        return AmcrestCameraExtraStoredData(
            motion_detection_enabled=self.motion_detection_enabled
        )

    async def async_added_to_hass(self) -> None:
        """
        Call when the camera is added to hass.
        Re-enable the motion detection state.
        """
        await super().async_added_to_hass()
        extra_data: ExtraStoredData | None
        if (
            extra_data := await self.async_get_last_extra_data()
        ) is not None and AmcrestCameraExtraStoredData(
            **extra_data.as_dict()
        ).motion_detection_enabled:
            await self.async_enable_motion_detection()

    async def async_turn_on(self) -> None:
        """
        Disable 'Privacy Mode'.
        The Camera does not support remote On/Off,
        however the functionality of Privacy Mode is similar.
        It will disable the feed and point the camera down and into its own base.
        """
        await self.coordinator.api.async_set_privacy_mode_on(False)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """
        Enable 'Privacy Mode'.
        The Camera does not support remote On/Off,
        however the functionality of Privacy Mode is similar.
        It will disable the feed and point the camera
        down and into its own base.
        """
        await self.coordinator.api.async_set_privacy_mode_on(True)
        await self.coordinator.async_refresh()
        self.async_write_ha_state()

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection."""
        self.coordinator.async_enable_event_listener()
        self.async_write_ha_state()

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection."""
        await self.coordinator.async_disable_event_listener()
        self.async_write_ha_state()

    @property
    def motion_detection_enabled(self) -> bool:
        """Motion detection listener is running."""
        return self.coordinator.is_listening_for_events

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image response from the camera."""
        if self._attr_is_on:
            return bytes(
                await self.coordinator.api.async_snapshot(subtype=self._stream_type)
            )
        return None

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        if self._attr_is_streaming:
            return str(
                await self.coordinator.api.async_get_rtsp_url(subtype=self._stream_type)
            )
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_is_on = not self.coordinator.amcrest_data.privacy_mode_on
        self._attr_is_streaming = not self.coordinator.amcrest_data.privacy_mode_on
        self.async_write_ha_state()
