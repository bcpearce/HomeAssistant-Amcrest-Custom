"""Define test fixtures for Amcrest."""

from collections.abc import Generator  # pylint: disable=import-error
from ipaddress import IPv4Address
from typing import Any

import pytest
import yarl
from amcrest_api.config import Config as AmcrestFixedConfig
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TYPE,
    CONF_URL,
    CONF_USERNAME,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.amcrest.const import CONF_MDNS, DOMAIN

from .const import MOCK_FIXED_CONFIG

TEST_IP_ADDRESS: str = "10.0.0.2"


# pylint: disable=unused-argument
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Generator[None]:
    """Enable custom integrations."""
    yield


@pytest.fixture(name="user_input_valid_connection")
def fixture_user_input_valid_connection() -> dict[str, Any]:
    """User input for valid connection in flow."""
    return {
        CONF_URL: str(yarl.URL.build(scheme="http", host=TEST_IP_ADDRESS, port=80)),
        CONF_USERNAME: "TESTUSER",
        CONF_PASSWORD: "TESTPASS",
    }


@pytest.fixture(name="mock_discovery_info")
def fixture_mock_discovery_info() -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=IPv4Address(TEST_IP_ADDRESS),
        ip_addresses=[IPv4Address(TEST_IP_ADDRESS)],
        port=80,
        hostname="AMC_TEST.local.",
        type="_http._tcp.local.",
        name="AMC_TEST._http._tcp.local.",
        properties={
            "host": "AMC_TEST",
            "mac": "a0:60:32:ff:ff:ff",
            "ip": "10.0.0.10",
            "subnet": "255.255.255.0",
            "gw": "10.0.0.1",
            "dns1": "8.8.8.8",
            "dns2": "8.8.4.4",
        },
    )


@pytest.fixture(name="mock_config_entry")
def fixture_mock_config_entry(
    user_input_valid_connection: dict[str, Any],
) -> MockConfigEntry:
    """Fixture for a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={**user_input_valid_connection, CONF_NAME: "AMC_TEST"},
    )


@pytest.fixture(name="mock_zeroconf_config_entry")
def fixture_mock_zeroconf_config_entry(
    user_input_valid_connection: dict[str, Any],
) -> MockConfigEntry:
    """Fixture for a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "AMC_TEST",
            CONF_MDNS: {
                CONF_TYPE: "_http._tcp_.local.",
                CONF_NAME: "AMC_TEST._http._tcp.local.",
            },
            CONF_USERNAME: "TESTUSER",
            CONF_PASSWORD: "TESTPASS",
        },
    )


@pytest.fixture(name="mock_fixed_config")
def fixture_mock_fixed_config() -> AmcrestFixedConfig:
    """Fixture for mock physical config."""
    return MOCK_FIXED_CONFIG
