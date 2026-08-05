"""Test the Spicetify media player entity."""

from unittest.mock import AsyncMock

from homeassistant.components.media_player import (
    ATTR_MEDIA_REPEAT,
    ATTR_MEDIA_SEEK_POSITION,
    ATTR_MEDIA_SHUFFLE,
    ATTR_MEDIA_VOLUME_LEVEL,
    SERVICE_MEDIA_NEXT_TRACK,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_PREVIOUS_TRACK,
    SERVICE_MEDIA_SEEK,
    SERVICE_REPEAT_SET,
    SERVICE_SHUFFLE_SET,
    SERVICE_VOLUME_SET,
    RepeatMode,
)
from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)
from spicetify import RepeatMode as SpicetifyRepeatMode


async def test_media_player_commands(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Test media player entity services."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    hub = mock_config_entry.runtime_data
    hub.is_connected = True
    hub._notify_connection_update()
    await hass.async_block_till_done()

    entity_id = "media_player.spicetify_desktop_client_9090"

    # Test Play
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PLAY,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_spotify_server.play.assert_called_once()

    # Test Pause
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PAUSE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_spotify_server.pause.assert_called_once()

    # Test Next Track
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_NEXT_TRACK,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_spotify_server.next_song.assert_called_once()

    # Test Previous Track
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PREVIOUS_TRACK,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_spotify_server.previous_song.assert_called_with(force=False)

    # Test Volume Set
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_VOLUME_LEVEL: 0.8},
        blocking=True,
    )
    mock_spotify_server.set_volume.assert_called_with(80.0)

    # Test Seek
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_SEEK,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_SEEK_POSITION: 45.0},
        blocking=True,
    )
    mock_spotify_server.seek.assert_called_with(45000.0)

    # Test Repeat Set
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_REPEAT_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_REPEAT: RepeatMode.ONE},
        blocking=True,
    )
    mock_spotify_server.set_repeat.assert_called_with(SpicetifyRepeatMode.TRACK)

    # Test Shuffle Set
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_SHUFFLE_SET,
        {ATTR_ENTITY_ID: entity_id, ATTR_MEDIA_SHUFFLE: True},
        blocking=True,
    )
    mock_spotify_server.set_shuffle.assert_called_with(True)

    # Test Favorite (async_set_favorite directly on entity)
    component = hass.data["entity_components"][MEDIA_PLAYER_DOMAIN]
    entity = component.get_entity(entity_id)
    assert entity is not None
    await entity.async_set_favorite(True)
    mock_spotify_server.set_heart.assert_called_with(True)
