"""Dataclass used by integration."""

from dataclasses import dataclass, field
from typing import Any

from amcrest_api.event import VideoMotionEvent
from amcrest_api.imaging import VideoDayNight, VideoImageControl
from amcrest_api.ptz import PtzPresetData, PtzStatusData
from amcrest_api.storage import StorageDeviceInfo


@dataclass
class AmcrestData:
    """Represents data from Camera."""

    ptz_presets: list[PtzPresetData] = field(default_factory=list)
    last_video_motion_event: VideoMotionEvent | None = None
    privacy_mode_on: bool | None = None  # doubles as on/off
    smart_track_on: bool | None = None
    lighting: Any | None = None  # LightingConfigData
    ptz_status: PtzStatusData | None = None
    storage_info: list[StorageDeviceInfo] = field(default_factory=list)
    video_image_control: list[VideoImageControl] = field(default_factory=list)
    video_input_day_night: list[list[VideoDayNight]] = field(default_factory=list)
