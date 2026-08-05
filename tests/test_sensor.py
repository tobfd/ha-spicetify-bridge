"""Test Spicetify Bridge sensors."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.spicetify_bridge import async_setup_entry


async def test_sensors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    _mock_spotify_server: AsyncMock,
) -> None:
    """Test sensor states."""
    mock_config_entry.add_to_hass(hass)
    await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()

    connection_state = hass.states.get(
        "sensor.spicetify_desktop_client_9090_connection_status"
    )
    assert connection_state is not None
    assert connection_state.state in ["connected", "disconnected"]

    latency_state = hass.states.get("sensor.spicetify_desktop_client_9090_ping_latency")
    assert latency_state is not None
