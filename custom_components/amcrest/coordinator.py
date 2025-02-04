"""Data coordinator for Amcrest integration."""

import asyncio
from asyncio import Task
from dataclasses import asdict
from datetime import timedelta
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

    async def async_get_fixed_config(self) -> AmcrestFixedConfig:
        """Obtain the fixed parameters of the camera."""
        return await self.api.async_get_fixed_config()

    async def async_poll_endpoints(self) -> AmcrestData:
        """Poll the endpoints for entity data."""

        kw_names = [
            "ptz_presets",
            "privacy_mode_on",
            "lighting",
            "ptz_status",
            "smart_track_on",
            "storage_info",
            "video_image_control",
            "video_input_day_night",
        ]

        tasks = [
            asyncio.create_task(self.api.async_ptz_preset_info),
            asyncio.create_task(self.api.async_get_privacy_mode_on()),
            asyncio.create_task(self.api.async_lighting_config),
            asyncio.create_task(self.api.async_ptz_status),
            asyncio.create_task(self.api.async_get_smart_track_on()),
            asyncio.create_task(self.api.async_storage_info),
            asyncio.create_task(self.api.async_video_image_control),
            asyncio.create_task(self.api.async_get_video_in_day_night()),
        ]

        results = await asyncio.gather(*tasks)

        # motion is special as it is a push endpoint, append the existing one
        kw_names.append("last_video_motion_event")
        results.append(self.amcrest_data.last_video_motion_event)

        return AmcrestData(**dict(zip(kw_names, results, strict=False)))

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
        return {(DOMAIN, str(self.fixed_config.serial_number))}

    @property
    def connections(self) -> set[tuple[str, str]]:
        return {
            (
                CONNECTION_NETWORK_MAC,
                self.fixed_config.session_physical_address,
            )
        }
