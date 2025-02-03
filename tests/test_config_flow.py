"""Test Config Flow."""

from typing import Any
from unittest.mock import AsyncMock, patch

from amcrest_api.config import Config as AmcrestFixedConfig
from amcrest_api.const import StreamType
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import SOURCE_USER, SOURCE_ZEROCONF
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.amcrest.const import CONF_STREAMS, DOMAIN


async def test_config_flow(
    hass: HomeAssistant,
    user_input_valid_connection: dict[str, Any],
    mock_fixed_config: AmcrestFixedConfig,
) -> None:
    """Test we get the form."""

    with (
        patch(
            "custom_components.amcrest.config_flow.AmcrestApiCamera.async_get_fixed_config",
            new_callable=AsyncMock,
            return_value=mock_fixed_config,
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM

        # input valid configuration
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input_valid_connection,
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.FORM

        # configure name and streams
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_NAME: "AMC_TEST", CONF_STREAMS: [str(StreamType.MAIN)]},
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # try to add a second of the same config, and observe config abort
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        await hass.async_block_till_done()

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input_valid_connection,
        )
        assert result["type"] is FlowResultType.ABORT

        await hass.async_block_till_done()


async def test_zeroconf_flow(
    hass: HomeAssistant,
    mock_discovery_info: ZeroconfServiceInfo,
    mock_fixed_config: AmcrestFixedConfig,
    user_input_valid_connection: dict[str, Any],
) -> None:
    """Test Config using Zeroconf autodetection."""

    result = await hass.config_entries.flow.async_init(
        DOMAIN, data=mock_discovery_info, context={"source": SOURCE_ZEROCONF}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "custom_components.amcrest.config_flow.AmcrestApiCamera.async_get_fixed_config",
            new_callable=AsyncMock,
            return_value=mock_fixed_config,
        ),
    ):
        # configure auth
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {k: user_input_valid_connection[k] for k in {CONF_USERNAME, CONF_PASSWORD}},
        )
        await hass.async_block_till_done()

        # configure name and streams
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_NAME: "AMC_TEST", CONF_STREAMS: [str(StreamType.MAIN)]},
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY

        assert result["type"] is FlowResultType.CREATE_ENTRY
