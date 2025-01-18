"""Data coordinator for Amcrest integration."""

from asyncio import Task
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from logging import Logger, getLogger
from typing import Any

from amcrest_api.camera import Camera as AmcrestApiCamera
from amcrest_api.config import Config as AmcrestFixedConfig
from amcrest_api.event import EventMessageType, VideoMotionEvent
from amcrest_api.ptz import PtzPresetData, PtzStatusData

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, MANUFACTURER

_LOGGER: Logger = getLogger(__package__)


@dataclass
class AmcrestData:
    """Represents data from Camera."""

    ptz_presets: list[PtzPresetData] = field(default_factory=list)
    last_video_motion_event: VideoMotionEvent | None = None
    privacy_mode_on: bool = True  # doubles as on/off
    lighting: Any | None = None  # LightingConfigData
    ptz_status: PtzStatusData | None = None


class AmcrestDataCoordinator(DataUpdateCoordinator):
    """Amcrest camera update coordinator."""

    _event_listener_task: Task | None = None
    fixed_config: AmcrestFixedConfig
    amcrest_data: AmcrestData
    data: dict[str, Any]

    def __init__(self, hass: HomeAssistant, api: AmcrestApiCamera) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Amcrest Data Coordinator",
            update_interval=timedelta(seconds=30),
        )
        self.api = api
        self.fixed_config = AmcrestFixedConfig
        self.amcrest_data = AmcrestData()
        self.data = asdict(self.amcrest_data)

    async def _async_setup(self) -> None:
        self.fixed_config = await self.api.async_read_physical_config()

    async def _async_update_data(self) -> dict[str, Any]:
        self.amcrest_data.ptz_presets = await self.api.async_ptz_preset_info
        self.amcrest_data.privacy_mode_on = await self.api.async_get_privacy_mode_on()
        self.amcrest_data.lighting = await self.api.async_lighting_config
        self.amcrest_data.ptz_status = await self.api.async_ptz_status
        return asdict(self.amcrest_data)

    def async_enable_event_listener(self) -> None:
        """Enable the event listener."""
        if self._event_listener_task is None:
            self._event_listener_task = self.hass.async_create_task(
                self.async_listen_for_camera_events()
            )
        self.async_update_listeners()

    async def async_disable_event_listener(self) -> None:
        """Disable the event listener."""
        if self._event_listener_task is not None:
            try:
                self._event_listener_task.cancel()
                await self._event_listener_task
            finally:
                self._event_listener_task = None
        self.async_update_listeners()

    async def async_listen_for_camera_events(self) -> None:
        """Listen for events."""
        try:
            _LOGGER.debug("Begin listening for motion events")
            async for event in self.api.async_listen_events(
                filter_events=[EventMessageType.VideoMotion]
            ):
                _LOGGER.debug(event)
                if isinstance(event, VideoMotionEvent):
                    self.amcrest_data.last_video_motion_event = event
                    self.async_update_listeners()
        finally:
            _LOGGER.debug("Finished listening for motion events")

    @property
    def is_listening_for_events(self) -> bool:
        """Indicate the listener is active."""
        return self._event_listener_task is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Device info for any entity using this coordinator."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.fixed_config.serial_number))},
            connections={
                (
                    CONNECTION_NETWORK_MAC,
                    self.fixed_config.session_physical_address,
                )
            },
            manufacturer=MANUFACTURER,
            sw_version=self.fixed_config.software_version,
            name=self.fixed_config.machine_name,
        )
