"""Test integration setup and unload lifecycles."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.spicetify_bridge import (
    async_setup_entry,
    async_unload_entry,
)


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Test setting up and unloading a config entry."""
    mock_config_entry.add_to_hass(hass)

    assert await async_setup_entry(hass, mock_config_entry)
    await hass.async_block_till_done()

    assert mock_config_entry.runtime_data is not None
    mock_spotify_server.start.assert_called_once()

    assert await async_unload_entry(hass, mock_config_entry)
    await hass.async_block_till_done()

    mock_spotify_server.stop.assert_called_once()
