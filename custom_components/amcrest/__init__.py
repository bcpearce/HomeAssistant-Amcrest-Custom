"""Support for Amcrest IP cameras."""

from __future__ import annotations

from logging import Logger, getLogger

from amcrest_api.camera import Camera as AmcrestApiCamera

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import ssl as hass_ssl

from .coordinator import AmcrestDataCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CAMERA,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type AmcrestConfigEntry = ConfigEntry[AmcrestDataCoordinator]

_LOGGER: Logger = getLogger(__package__)


async def async_setup_entry(hass: HomeAssistant, entry: AmcrestConfigEntry) -> bool:
    """Set up an Amcrest camera integration entry."""
    scheme, url_or_ip = entry.data[CONF_HOST].split("://")
    api = AmcrestApiCamera(
        host=url_or_ip,
        port=entry.data[CONF_PORT],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        scheme=scheme,
        verify=hass_ssl.get_default_context(),
    )
    coordinator = AmcrestDataCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AmcrestConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.async_disable_event_listener()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
