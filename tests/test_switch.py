"""Test Spicetify Bridge switches."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
)
from homeassistant.components.switch import (
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)


async def test_liked_track_switch(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Test liked track switch entity."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    hub = mock_config_entry.runtime_data
    hub.is_connected = True
    hub.player_state = MagicMock()
    hub.player_state.is_hearted = False
    hub.player_state.track = MagicMock()
    hub._notify_connection_update()
    hub._notify_state_update()
    await hass.async_block_till_done()

    entity_id = "switch.spicetify_desktop_client_9090_liked_track"

    # Turn Switch ON (Heart track)
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_spotify_server.set_heart.assert_called_with(True)

    # Turn Switch OFF (Unlike track)
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_spotify_server.set_heart.assert_called_with(False)
