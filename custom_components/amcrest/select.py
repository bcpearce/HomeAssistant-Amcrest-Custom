"""Select entities for Amcrest."""

from amcrest_api.imaging import (
    CONFIG_NO_DICT,
    ConfigNo,
    Rotate90Flag,
    VideoDayNight,
    VideoImageControl,
    VideoMode,
)
from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import AmcrestConfigEntry
from .const import RotationOption
from .coordinator import AmcrestDataCoordinator
from .entity import AmcrestEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmcrestConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the IP Camera from config entry."""

    if entry.runtime_data.fixed_config.ptz_capabilities.preset:
        async_add_entities([PtzPresetSelectEntity(coordinator=entry.runtime_data)])

    async_add_entities([ImageRotationSelectEntity(coordinator=entry.runtime_data)])
    async_add_entities(
        [
            VideoInputDayNight(coordinator=entry.runtime_data, config_no=config_no)
            for config_no in ConfigNo
        ]
    )


class PtzPresetSelectEntity(AmcrestEntity, SelectEntity):
    """Selector for PTZ presets."""

    _attr_has_entity_name = True
    _attr_translation_key = "ptz_preset"

    def __init__(self, coordinator: AmcrestDataCoordinator) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)
        self._attr_options = self._attr_options = [
            preset.name for preset in self.coordinator.amcrest_data.ptz_presets
        ]
        self._attr_current_option = None
        self._attr_unique_id = f"{coordinator.fixed_config.serial_number}-ptz_preset"

    async def async_select_option(self, option: str) -> None:
        """Select preset by name."""
        preset = next(
            preset
            for preset in self.coordinator.amcrest_data.ptz_presets
            if preset.name == option
        )
        self._attr_current_option = preset.name
        await self.coordinator.api.async_ptz_move_to_preset(preset.index)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_options = [
            preset.name for preset in self.coordinator.amcrest_data.ptz_presets
        ]
        try:
            ptz_status = self.coordinator.amcrest_data.ptz_status
            preset = next(
                preset
                for preset in self.coordinator.amcrest_data.ptz_presets
                if ptz_status is not None
                and int(preset.index) == int(ptz_status.preset_id)
            )
            self._attr_current_option = preset.name
        except StopIteration:
            self._attr_current_option = None
        self.async_write_ha_state()


def rotation_from_amcrest(control: VideoImageControl) -> RotationOption | None:
    """Convert the VideoImageControl information to RotationOption"""
    if control is None:
        return None
    if control.flip:
        return RotationOption.FLIP_180
    elif control.rotate_90 == Rotate90Flag.CLOCKWISE_90:
        return RotationOption.CLOCKWISE_90
    elif control.rotate_90 == Rotate90Flag.COUNTERCLOCKWISE_90:
        return RotationOption.CLOCKWISE_270
    else:
        return RotationOption.NONE


class ImageRotationSelectEntity(AmcrestEntity, SelectEntity):
    """Selector for feed rotation."""

    _lut = {
        RotationOption.NONE: VideoImageControl(
            flip=False, rotate_90=Rotate90Flag.NO_ROTATE, mirror=False
        ),
        RotationOption.CLOCKWISE_90: VideoImageControl(
            flip=False, rotate_90=Rotate90Flag.CLOCKWISE_90, mirror=False
        ),
        RotationOption.FLIP_180: VideoImageControl(
            flip=True, rotate_90=Rotate90Flag.NO_ROTATE, mirror=False
        ),
        RotationOption.CLOCKWISE_270: VideoImageControl(
            flip=False, rotate_90=Rotate90Flag.COUNTERCLOCKWISE_90, mirror=False
        ),
    }

    _attr_icon = "mdi:rotate-right-variant"
    _attr_has_entity_name = True
    _attr_translation_key = "video_image_control"

    def __init__(self, coordinator: AmcrestDataCoordinator, channel: int = 0) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)
        self._channel = channel
        self._attr_unique_id = (
            f"{coordinator.fixed_config.serial_number}-video_image_control-{channel}"
        )
        self._attr_options = [x for x in RotationOption]
        if len(self.coordinator.amcrest_data.video_image_control) > 0:
            self._attr_current_option = rotation_from_amcrest(
                coordinator.amcrest_data.video_image_control[self._channel]
            )
        else:
            self._attr_current_option = None

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        await self.coordinator.api.async_set_video_image_control(
            self._lut[RotationOption(option)]
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        if len(self.coordinator.amcrest_data.video_image_control) > 0:
            self._attr_current_option = rotation_from_amcrest(
                self.coordinator.amcrest_data.video_image_control[self._channel]
            )
        else:
            self._attr_current_option = None
        self.async_write_ha_state()


class VideoInputDayNight(AmcrestEntity, SelectEntity):
    """Select for Input Day/Night mode."""

    _attr_icon = "mdi:theme-light-dark"
    _attr_has_entity_name = True
    _attr_translation_key = "video_input_day_night"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: AmcrestDataCoordinator, config_no: ConfigNo, channel: int = 1
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator=coordinator)
        self._channel = channel
        self._config_no = config_no
        self._attr_unique_id = f"{coordinator.fixed_config.serial_number}-video_input_day_night-{channel}-{config_no}"  # noqa: E501
        self._attr_options = [x for x in VideoMode]

        self._attr_current_option = self.coordinator.amcrest_data.video_input_day_night[
            self._channel - 1
        ][self._config_no].mode

        self._attr_translation_placeholders = {"config_desc": ""}
        if (config_desc := CONFIG_NO_DICT.get(self._config_no)) is not None:
            self._attr_translation_placeholders["config_desc"] = (
                f"({config_desc} Profile)"
            )

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        config: VideoDayNight = self.coordinator.amcrest_data.video_input_day_night[
            self._channel - 1
        ][self._config_no]
        config.mode = VideoMode(option)
        await self.coordinator.api.async_set_video_in_day_night(
            config,
            self._config_no,
            channel=self._channel,
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        try:
            self._attr_current_option = (
                self.coordinator.amcrest_data.video_input_day_night[self._channel - 1][
                    self._config_no
                ].mode
            )
        except IndexError:
            self._attr_current_option = None
        self.async_write_ha_state()
