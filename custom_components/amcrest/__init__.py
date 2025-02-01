"""Support for Amcrest IP cameras."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import yarl
from amcrest_api.camera import Camera as AmcrestApiCamera
from amcrest_api.ptz import PtzBasicMove, PtzPresetData, PtzRelativeMove
from homeassistant.components import zeroconf
from homeassistant.components.zeroconf import IPVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_URL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.exceptions import ConfigEntryError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.util import ssl as hass_ssl

from .const import DOMAIN
from .coordinator import AmcrestDataCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from zeroconf import ServiceInfo

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type AmcrestConfigEntry = ConfigEntry[AmcrestDataCoordinator]

SERVICE_PAN = "pan"
SERVICE_PAN_DIRECTION = "pan_direction"
SERVICE_TILT = "tilt"
SERIVCE_TILT_DIRECTION = "tilt_direction"
_ZOOM = "zoom"
_ZOOM_DIRECTION = "zoom_direction"

SERVICE_UPDATE_PTZ_PRESET = "update_ptz_preset"
SERVICE_CLEAR_PTZ_PRESET = "remove_ptz_preset"
SERVICE_PRESET_ID = "preset_id"
SERVICE_PRESET_NAME = "preset_name"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


def async_coordinator_from_service_call(
    call: ServiceCall,
) -> AmcrestDataCoordinator:
    """Get the coordinator from a call with a device ID."""
    registry = dr.async_get(call.hass)
    entry_id = registry.async_get(call.data["device_id"]).primary_config_entry
    if entry_id is None:
        raise ServiceValidationError(
            DOMAIN,
            "device_not_found",
            translation_placeholders={"device_id": call.data["device_id"]},
        )
    coordinator: AmcrestDataCoordinator = call.hass.config_entries.async_get_entry(
        entry_id
    ).runtime_data
    return coordinator


async def async_handle_ptz(call: ServiceCall) -> None:
    """Handle PTZ service calls."""
    coordinator = async_coordinator_from_service_call(call)
    if call.data.get("move_mode") == "relative":
        move = PtzRelativeMove()
        if (direction := call.data.get(SERVICE_PAN_DIRECTION)) is not None:
            move.horizontal = call.data.get("distance", 0.0) * (
                -1.0 if direction == "left" else 1.0
            )
        elif (direction := call.data.get(SERIVCE_TILT_DIRECTION)) is not None:
            move.vertical = call.data.get("distance", 0.0) * (
                -1.0 if direction == "down" else 1.0
            )
        await coordinator.api.async_ptz_move_relative(move)

    elif (move_mode := call.data.get("move_mode")) in ["continuous", "stop"]:
        pan_direction = call.data.get(SERVICE_PAN_DIRECTION)
        tilt_direction = call.data.get(SERIVCE_TILT_DIRECTION)
        move = PtzBasicMove(pan_direction or tilt_direction)
        if move_mode == "continuous":
            if (speed := call.data.get("speed")) is not None:
                move.speed = speed
            seconds = call.data.get("continuous_duration_seconds")
            duration = timedelta(seconds=seconds) if seconds is not None else None
            await coordinator.api.async_ptz_move(move, duration)
        elif move_mode == "stop":
            await coordinator.api.async_ptz_stop(move)
    await coordinator.async_request_refresh()


async def async_handle_update_ptz_preset(call: ServiceCall) -> None:
    """Handles saving a new PTZ preset, or updating an existing one."""
    coordinator = async_coordinator_from_service_call(call)
    index = int(call.data[SERVICE_PRESET_ID])
    preset = PtzPresetData(
        index=index, name=call.data.get(SERVICE_PRESET_NAME, f"Preset{index}")
    )
    await coordinator.api.async_set_ptz_preset(preset)
    await coordinator.async_request_refresh()


async def async_handle_clear_ptz_preset(call: ServiceCall) -> None:
    """Handles clearing a PTZ preset."""
    coordinator = async_coordinator_from_service_call(call)
    index = int(call.data[SERVICE_PRESET_ID])
    await coordinator.api.async_clear_ptz_preset(index)
    await coordinator.async_request_refresh()


# pylint: disable=unused-argument
async def async_setup(hass: HomeAssistant, config: Any) -> bool:
    """Set up the integration."""
    hass.services.async_register(DOMAIN, SERVICE_PAN, async_handle_ptz)
    hass.services.async_register(DOMAIN, SERVICE_TILT, async_handle_ptz)
    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_PTZ_PRESET, async_handle_update_ptz_preset
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_PTZ_PRESET, async_handle_clear_ptz_preset
    )
    return True


async def async_get_service_info(
    hass: HomeAssistant, mdns_setup_data: dict[str, str]
) -> ServiceInfo:
    zc = await zeroconf.async_get_async_instance(hass)
    service_info = await zc.async_get_service_info(
        mdns_setup_data[CONF_TYPE], mdns_setup_data[CONF_NAME]
    )
    if service_info is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="device_detection_failed",
            translation_placeholders={"mdns_name": mdns_setup_data[CONF_NAME]},
        )
    return service_info


async def async_setup_entry(hass: HomeAssistant, entry: AmcrestConfigEntry) -> bool:
    """Set up an Amcrest camera integration entry."""
    if (mdns_setup_data := entry.data.get("mdns")) is not None:
        # only support V4
        service_info: ServiceInfo = await async_get_service_info(hass, mdns_setup_data)
        ip, port = (
            str(service_info.ip_addresses_by_version(IPVersion.V4Only)[0]),
            service_info.port,
        )
        url = yarl.URL.build(
            scheme="http",
            host=ip,
            port=port,
        )
    else:
        url = yarl.URL(entry.data[CONF_URL])

    api = AmcrestApiCamera(
        host=url.host,
        port=url.port,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        scheme=url.scheme,
        verify=hass_ssl.get_default_context(),
    )
    coordinator = AmcrestDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AmcrestConfigEntry) -> bool:
    """Unload a config entry."""
    did_unload = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await entry.runtime_data.async_disable_event_listener()
    return did_unload
