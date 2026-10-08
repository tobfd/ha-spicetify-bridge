"""Test the Spicetify Bridge config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.spicetify_bridge.config_flow import (
    _can_bind_port,
    _validate_ssl_files,
)
from custom_components.spicetify_bridge.const import (
    CONF_API_KEY,
    CONF_CERTFILE,
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_KEYFILE,
    CONF_PORT,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

BIND_PORT = "custom_components.spicetify_bridge.config_flow._can_bind_port"
VALIDATE_SSL = "custom_components.spicetify_bridge.config_flow._validate_ssl_files"


async def test_flow_user_success_no_ssl(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test successful user step without SSL."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with patch(BIND_PORT, return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "0.0.0.0",
                CONF_PORT: 9090,
                CONF_ENABLE_SSL: False,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Spicetify Bridge (Port 9090)"
    assert result2["data"] == {
        CONF_HOST: "0.0.0.0",
        CONF_PORT: 9090,
        CONF_API_KEY: "",
        CONF_ENABLE_SSL: False,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_flow_user_ssl_step(hass: HomeAssistant) -> None:
    """Test user step leading to SSL setup and file validation."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(BIND_PORT, return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: "0.0.0.0",
                CONF_PORT: 9090,
                CONF_ENABLE_SSL: True,
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["step_id"] == "ssl"

    # Invalid SSL file paths show an error and keep the form open
    with patch(VALIDATE_SSL, return_value=False):
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_CERTFILE: "/invalid/cert.pem",
                CONF_KEYFILE: "/invalid/key.pem",
            },
        )

    assert result3["type"] is FlowResultType.FORM
    assert result3["errors"] == {"base": "ssl_file_not_found"}

    # The user can recover by entering valid paths
    with patch(VALIDATE_SSL, return_value=True):
        result4 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {
                CONF_CERTFILE: "/ssl/cert.pem",
                CONF_KEYFILE: "/ssl/key.pem",
            },
        )
        await hass.async_block_till_done()

    assert result4["type"] is FlowResultType.CREATE_ENTRY
    assert result4["data"][CONF_CERTFILE] == "/ssl/cert.pem"
    assert result4["data"][CONF_KEYFILE] == "/ssl/key.pem"


async def test_flow_user_port_in_use_recovers(hass: HomeAssistant) -> None:
    """Test that a port that cannot be bound shows an error and the flow recovers."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    user_input = {CONF_HOST: "0.0.0.0", CONF_PORT: 9090, CONF_ENABLE_SSL: False}

    with patch(BIND_PORT, return_value=False):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}

    with patch(BIND_PORT, return_value=True):
        result3 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
        await hass.async_block_till_done()
    assert result3["type"] is FlowResultType.CREATE_ENTRY


async def test_flow_user_already_configured(hass: HomeAssistant) -> None:
    """Test that the same host and port cannot be configured twice."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="spicetify_bridge_0.0.0.0_9090",
        data={CONF_HOST: "0.0.0.0", CONF_PORT: 9090, CONF_ENABLE_SSL: False},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    with patch(BIND_PORT, return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "0.0.0.0", CONF_PORT: 9090, CONF_ENABLE_SSL: False},
        )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow, including SSL validation and recovery."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "0.0.0.0", CONF_PORT: 9090, CONF_ENABLE_SSL: False},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    options = {
        CONF_API_KEY: "new-secret",
        CONF_ENABLE_SSL: True,
        CONF_CERTFILE: "/ssl/cert.pem",
        CONF_KEYFILE: "/ssl/key.pem",
    }
    with patch(VALIDATE_SSL, return_value=False):
        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"], options
        )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "ssl_file_not_found"}

    with patch(VALIDATE_SSL, return_value=True):
        result3 = await hass.config_entries.options.async_configure(
            result["flow_id"], options
        )
        await hass.async_block_till_done()
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_API_KEY] == "new-secret"
    assert entry.options[CONF_ENABLE_SSL] is True


def test_validate_ssl_files(tmp_path) -> None:
    """Test the certificate file check."""
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    cert.write_text("cert")

    assert not _validate_ssl_files(str(cert), str(key))
    key.write_text("key")
    assert _validate_ssl_files(str(cert), str(key))


def test_can_bind_port() -> None:
    """Test the port availability check for a free and a busy port."""
    with patch(
        "custom_components.spicetify_bridge.config_flow.socket.socket"
    ) as mock_socket:
        assert _can_bind_port("0.0.0.0", 9090)
        mock_socket.return_value.bind.assert_called_once_with(("0.0.0.0", 9090))

        mock_socket.return_value.bind.side_effect = OSError("Address already in use")
        assert not _can_bind_port("0.0.0.0", 9090)
        assert mock_socket.return_value.close.call_count == 2
