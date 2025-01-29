"""Config flow for Amcrest."""

from typing import TYPE_CHECKING, Any

import voluptuous as vol
import yarl
from amcrest_api.camera import Camera as AmcrestApiCamera
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    ATTR_SERIAL_NUMBER,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_UNIQUE_ID,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.util import ssl as hass_ssl
from httpx import HTTPStatusError

from .const import CONF_MDNS, DOMAIN

if TYPE_CHECKING:
    from amcrest_api.config import Config as AmcrestFixedConfig

ZEROCONF_NAME = "camera_discovered_name"


class AmcrestConfigFlow(ConfigFlow, domain=DOMAIN):
    """Amcrest config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    _camera_api: AmcrestApiCamera
    _discovered: ZeroconfServiceInfo | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """User config flow step."""
        errors = {}
        if user_input is not None:
            try:
                # Validate connection and get object
                if self._discovered is not None:
                    url = yarl.URL.build(
                        scheme=("https" if self._discovered.port == 443 else "http"),
                        host=self._discovered.host,
                        port=self._discovered.port,
                    )
                    self._config.setdefault(CONF_MDNS, {})[CONF_TYPE] = (
                        self._discovered.type
                    )
                    self._config[CONF_MDNS][CONF_NAME] = self._discovered.name
                else:
                    url = yarl.URL(user_input[CONF_URL])
                    self._config[CONF_URL] = url

                self._camera_api = AmcrestApiCamera(
                    host=url.host,
                    port=url.port,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    scheme=url.scheme,
                    verify=hass_ssl.get_default_context(),
                )
                config: AmcrestFixedConfig = (
                    await self._camera_api.async_get_fixed_config()
                )

                await self.async_set_unique_id(config.session_physical_address)
                self._abort_if_unique_id_configured(
                    updates={
                        ATTR_SERIAL_NUMBER: config.serial_number,
                        CONF_MAC: config.session_physical_address,
                    }
                )

                self._config[ATTR_SERIAL_NUMBER] = config.serial_number
                self._config[CONF_UNIQUE_ID] = config.serial_number
                self._config[CONF_MAC] = config.session_physical_address
                # Successfully connected, merge the user input to the config
                self._config[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                self._config[CONF_USERNAME] = user_input[CONF_USERNAME]
                return self.async_create_entry(
                    title=self._config[ATTR_SERIAL_NUMBER], data=self._config
                )
            except HTTPStatusError as e:
                errors[CONF_USERNAME] = e.response.text

        description_placeholders = {"target_device": ""}
        if self._discovered:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
            description_placeholders = {
                "target_device": self._discovered.properties[CONF_HOST]
            }
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_URL, default="http://"): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.URL)
                    ),
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle discovery via Zeroconf."""
        mac = discovery_info.properties[CONF_MAC]

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(
            updates={
                CONF_HOST: discovery_info.host,
                CONF_MAC: mac,
            }
        )

        # build the hostname based on mDNS info
        self._discovered = discovery_info

        self.context["title_placeholders"] = {
            ZEROCONF_NAME: f"{discovery_info.properties['host']} ({discovery_info.ip_address.compressed})"  # noqa: E501
        }

        return await self.async_step_user()
