"""Test Spicetify Bridge buttons."""

from unittest.mock import AsyncMock

from homeassistant.components.button import (
    DOMAIN as BUTTON_DOMAIN,
)
from homeassistant.components.button import (
    SERVICE_PRESS,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.spicetify_bridge import async_setup_entry


async def test_button_press(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Test pressing button entities."""
    mock_config_entry.add_to_hass(hass)
    await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()

    # Press Force Previous Button
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.spicetify_desktop_client_9090_force_previous"},
        blocking=True,
    )
    mock_spotify_server.previous_song.assert_called_with(force=True)

    # Press Ping Button
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.spicetify_desktop_client_9090_ping_client"},
        blocking=True,
    )
    mock_spotify_server.ping.assert_called_once()
