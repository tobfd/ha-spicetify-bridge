"""Test the Spicetify Bridge config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.spicetify_bridge.const import (
    CONF_API_KEY,
    CONF_CERTFILE,
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_KEYFILE,
    CONF_PORT,
    DOMAIN,
)


async def test_flow_user_success_no_ssl(hass: HomeAssistant) -> None:
    """Test successful user step without SSL."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with patch(
        "custom_components.spicetify_bridge.config_flow._can_bind_port",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "0.0.0.0",
                CONF_PORT: 9090,
                CONF_ENABLE_SSL: False,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Spicetify Bridge (Port 9090)"
    assert result2["data"] == {
        CONF_HOST: "0.0.0.0",
        CONF_PORT: 9090,
        CONF_API_KEY: "",
        CONF_ENABLE_SSL: False,
    }


async def test_flow_user_ssl_step(hass: HomeAssistant) -> None:
    """Test user step leading to SSL setup and file validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.spicetify_bridge.config_flow._can_bind_port",
        return_value=True,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "0.0.0.0",
                CONF_PORT: 9090,
                CONF_ENABLE_SSL: True,
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "ssl"

    # Test invalid SSL file paths
    with patch(
        "custom_components.spicetify_bridge.config_flow._validate_ssl_files",
        return_value=False,
    ):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_CERTFILE: "/invalid/cert.pem",
                CONF_KEYFILE: "/invalid/key.pem",
            },
        )

    assert result3["type"] == FlowResultType.FORM
    assert result3["errors"] == {"base": "ssl_file_not_found"}

    # Test valid SSL file paths
    with patch(
        "custom_components.spicetify_bridge.config_flow._validate_ssl_files",
        return_value=True,
    ):
        result4 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_CERTFILE: "/ssl/cert.pem",
                CONF_KEYFILE: "/ssl/key.pem",
            },
        )
        await hass.async_block_till_done()

    assert result4["type"] == FlowResultType.CREATE_ENTRY
    assert result4["data"][CONF_CERTFILE] == "/ssl/cert.pem"
