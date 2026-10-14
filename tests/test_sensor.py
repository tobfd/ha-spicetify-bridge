"""Test Spicetify Bridge sensors."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

CONNECTION_SENSOR = "sensor.spicetify_desktop_client_9090_connection_status"
LATENCY_SENSOR = "sensor.spicetify_desktop_client_9090_ping_latency"


async def test_connection_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """The connection sensor stays available and reports the connection state."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(CONNECTION_SENSOR).state == "disconnected"

    hub = mock_config_entry.runtime_data
    hub._set_connected(True)
    await hass.async_block_till_done()

    state = hass.states.get(CONNECTION_SENSOR)
    assert state.state == "connected"
    assert state.attributes["options"] == ["connected", "disconnected"]


async def test_latency_sensor_is_disabled_by_default(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """The noisy diagnostic latency sensor is created but disabled by default."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entry = entity_registry.async_get(LATENCY_SENSOR)
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(LATENCY_SENSOR) is None


async def test_latency_sensor_reports_ping(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Once enabled, the latency sensor shows the last ping result."""
    mock_config_entry.add_to_hass(hass)
    entity_registry.async_get_or_create(
        "sensor",
        "spicetify_bridge",
        f"spicetify_bridge_{mock_config_entry.entry_id}_ping_latency",
        suggested_object_id="spicetify_desktop_client_9090_ping_latency",
        disabled_by=None,
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    await mock_config_entry.runtime_data.async_ping_client()
    await hass.async_block_till_done()

    assert hass.states.get(LATENCY_SENSOR).state == "12.5"
