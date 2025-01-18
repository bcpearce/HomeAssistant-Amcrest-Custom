"""Config flow for Amcrest."""

from typing import Any

from amcrest_api.camera import Camera as AmcrestApiCamera
from amcrest_api.config import Config as AmcrestFixedConfig
from httpx import HTTPStatusError
import voluptuous as vol

from homeassistant.components.dhcp import DhcpServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    ATTR_SERIAL_NUMBER,
    ATTR_SW_VERSION,
    CONF_ADDRESS,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_UNIQUE_ID,
    CONF_USERNAME,
)
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import ssl as hass_ssl

from .const import DEFAULT_PORT_HTTP, DOMAIN


class AmcrestConfigFlow(ConfigFlow, domain=DOMAIN):
    """Amcrest config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    _camera_api: AmcrestApiCamera

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config: dict[str, Any] = {}
        self._discovered: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """User config flow step."""
        errors = {}
        if user_input is not None:
            try:
                # Validate connection and get object
                scheme, url_or_ip = user_input[CONF_HOST].split("://")
                self._camera_api = AmcrestApiCamera(
                    host=url_or_ip,
                    port=user_input[CONF_PORT],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    scheme=scheme,
                    verify=hass_ssl.get_default_context(),
                )
                config: AmcrestFixedConfig = (
                    await self._camera_api.async_read_physical_config()
                )
                self._config[ATTR_SERIAL_NUMBER] = config.serial_number
                self._config[CONF_UNIQUE_ID] = config.serial_number
                self._config[CONF_MAC] = config.session_physical_address
                self._config[CONF_NAME] = config.machine_name
                self._config[ATTR_SW_VERSION] = config.software_version
                self._abort_if_unique_id_configured(
                    updates={ATTR_SERIAL_NUMBER: self._config[ATTR_SERIAL_NUMBER]}
                )
                # Successfully connected, merge the user input to the config
                self._config |= user_input
                return self.async_create_entry(
                    title=self._config[ATTR_SERIAL_NUMBER], data=self._config
                )
            except HTTPStatusError as e:
                errors[CONF_HOST] = e.response.text

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self._discovered.get(CONF_HOST, "http://")
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
                    vol.Required(CONF_PORT, default=DEFAULT_PORT_HTTP): int,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery via DHCP."""
        serial = discovery_info.hostname.upper()

        await self.async_set_unique_id(serial)
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: discovery_info.ip,
                CONF_ADDRESS: discovery_info.macaddress,
            }
        )

        self._discovered[CONF_HOST] = discovery_info.ip
        self._discovered[CONF_ADDRESS] = discovery_info.macaddress

        return await self.async_step_user()
