"""Data coordinator for Amcrest integration."""

import asyncio
from asyncio import Task
from dataclasses import asdict
from datetime import datetime, timedelta
from logging import Logger, getLogger
from typing import Any

from amcrest_api.camera import Camera as AmcrestApiCamera
from amcrest_api.config import Config as AmcrestFixedConfig
from amcrest_api.event import EventMessageType, VideoMotionEvent
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .data import AmcrestData

_LOGGER: Logger = getLogger(__package__)

PARALLEL_UPDATES = 0

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=120)


class AmcrestDataCoordinator(DataUpdateCoordinator):
    """Amcrest camera update coordinator."""

    _event_listener_task: Task | None = None
    _should_listen_for_events: bool = False
    amcrest_data: AmcrestData
    fixed_config: AmcrestFixedConfig
    api: AmcrestApiCamera
    data: dict[str, Any]

    def __init__(self, hass: HomeAssistant, api: AmcrestApiCamera) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Amcrest Data Coordinator",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.api = api
        self.amcrest_data = AmcrestData()
        self.data = asdict(self.amcrest_data)

    def _has_ptz_caps(self) -> bool:
        ptz_caps = self.fixed_config.ptz_capabilities
        return bool(
            ptz_caps.pan
            or ptz_caps.tilt
            or ptz_caps.zoom
            or ptz_caps.preset
            or ptz_caps.tour
        )

    async def async_get_fixed_config(self) -> AmcrestFixedConfig:
        """Obtain the fixed parameters of the camera."""
        # If there is a significant timedelta, fix the time.
        # The time resets to a default upon power cycling the camera.
        camera_time: datetime = await self.api.async_get_current_time()
        current_time = datetime.now()

        if abs(camera_time - current_time) > timedelta(days=1):
            _LOGGER.warning(
                "Camera's current time of %s, differs by more than one day from system time.",  # noqa E501
                camera_time,
            )
            _LOGGER.warning("Setting the time on the camera at %s", self.api.url)
            await self.api.async_set_current_time(current_time)
        return await self.api.async_get_fixed_config()

    async def async_poll_endpoints(self) -> AmcrestData:
        """Poll the endpoints for entity data."""
        kw_names = [
            "ptz_presets",
            "lighting",
            "storage_info",
            "video_image_control",
            "video_input_day_night",
        ]

        tasks: list[Task] = [
            asyncio.create_task(self.api.async_ptz_preset_info),
            asyncio.create_task(self.api.async_lighting_config),
            asyncio.create_task(self.api.async_storage_info),
            asyncio.create_task(self.api.async_video_image_control),
            asyncio.create_task(self.api.async_get_video_in_day_night()),
        ]

        if self._has_ptz_caps():
            kw_names.append("ptz_status")
            tasks.append(asyncio.create_task(self.api.async_ptz_status))

        if self.fixed_config.privacy_mode_available:
            tasks.append(asyncio.create_task(self.api.async_get_privacy_mode_on()))
            kw_names.append("privacy_mode_on")

        if self.fixed_config.smart_track_available:
            tasks.append(asyncio.create_task(self.api.async_get_smart_track_on()))
            kw_names.append("smart_track_on")

        results: list[Any] = await asyncio.gather(*tasks, return_exceptions=True)

        # motion is special as it is a push endpoint, append the existing one
        kw_names.append("last_video_motion_event")
        results.append(self.amcrest_data.last_video_motion_event)

        return AmcrestData(
            **dict(
                (k, v)
                for k, v in zip(kw_names, results, strict=False)
                if not isinstance(v, Exception)
            )
        )

    async def _async_setup(self) -> None:
        self.fixed_config = await self.async_get_fixed_config()

    async def _async_update_data(self) -> dict[str, Any]:
        self.amcrest_data = await self.async_poll_endpoints()
        # restore the listener if it failed unexpectedly
        if self._should_listen_for_events and not self.is_listening_for_events:
            self.async_enable_event_listener()
        return asdict(self.amcrest_data)

    @callback
    def async_enable_event_listener(self) -> None:
        """Enable the event listener."""
        if not self.is_listening_for_events:
            self._event_listener_task = self.config_entry.async_create_background_task(
                self.hass,
                self.async_listen_for_camera_events(),
                f"amcrest {self.data.get(CONF_NAME)}",
            )
            self._should_listen_for_events = True
        self.async_update_listeners()

    @callback
    async def async_disable_event_listener(self) -> None:
        """Disable the event listener."""
        if self._event_listener_task is not None:
            try:
                self._event_listener_task.cancel()
                await self._event_listener_task
            finally:
                self._event_listener_task = None
        self.async_update_listeners()
        self._should_listen_for_events = False

    async def async_listen_for_camera_events(self) -> None:
        """Listen for events."""
        try:
            _LOGGER.debug(
                "Begin listening for motion events on device %s",
                self.data.get(CONF_NAME),
            )
            async for event in self.api.async_listen_events(
                heartbeat_seconds=30, filter_events=[EventMessageType.VideoMotion]
            ):
                _LOGGER.debug(event)
                if isinstance(event, VideoMotionEvent):
                    self.amcrest_data.last_video_motion_event = event
                    self.async_update_listeners()
        except Exception as e:
            _LOGGER.error(
                "An exception occurred on event listener for device %s: %s",
                self.data.get(CONF_NAME),
                e,
            )
        except asyncio.CancelledError:
            _LOGGER.info(
                "Event listener for device %s cancelled", self.data.get(CONF_NAME)
            )
        finally:
            _LOGGER.debug(
                "Finished listening for motion events %s", self.data.get(CONF_NAME)
            )

    @property
    def is_listening_for_events(self) -> bool:
        """Indicate the listener is active."""
        return (
            self._event_listener_task is not None
            and not self._event_listener_task.done()
            and not self._event_listener_task.cancelled()
        )

    @property
    def identifiers(self) -> set[tuple[str, str]]:
        """Identifiers for device info."""
        return {(DOMAIN, str(self.fixed_config.serial_number))}

    @property
    def connections(self) -> set[tuple[str, str]]:
        """Connections for device info."""
        return {
            (
                CONNECTION_NETWORK_MAC,
                self.fixed_config.session_physical_address,
            )
        }
