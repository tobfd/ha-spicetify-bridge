"""Test Spicetify Bridge switches."""

from unittest.mock import AsyncMock

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

from custom_components.spicetify_bridge import async_setup_entry


async def test_liked_track_switch(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Test liked track switch entity."""
    mock_config_entry.add_to_hass(hass)
    await async_setup_entry(hass, mock_config_entry)
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
