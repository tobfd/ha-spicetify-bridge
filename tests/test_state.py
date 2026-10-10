"""Test how player state snapshots map to Home Assistant entity state."""

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.media_player import MediaPlayerState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from spicetify import PlayerState

MEDIA_PLAYER = "media_player.spicetify_desktop_client_9090"


def _state(**overrides) -> PlayerState:
    """Build a PlayerState the way the library parses an extension event."""
    payload = {
        "isPlaying": True,
        "volume": 0.42,
        "progress": 61000,
        "playerData": {
            "item": {
                "uri": "spotify:track:abc",
                "name": "Test Track",
                "duration": {"milliseconds": 180000},
                "artists": [{"name": "Artist", "uri": "spotify:artist:1"}],
            },
            "isBuffering": False,
        },
    }
    payload.update(overrides)
    return PlayerState.from_payload(payload, event_name="SongChanged")


@pytest.fixture
async def hub(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
):
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry.runtime_data


async def _push(hass: HomeAssistant, hub, state: PlayerState) -> None:
    hub._update_player_state(state)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("raw_volume", "expected_level"),
    [(0.42, 0.42), (0.01, 0.01), (0.005, 0.005), (1.0, 1.0), (0.0, 0.0)],
)
async def test_volume_is_not_converted_twice(
    hass: HomeAssistant, hub, raw_volume: float, expected_level: float
) -> None:
    """Regression test: Spotify at 1 % used to show up as 100 % in Home Assistant."""
    await _push(hass, hub, _state(volume=raw_volume))

    attributes = hass.states.get(MEDIA_PLAYER).attributes
    assert attributes["volume_level"] == pytest.approx(expected_level)


async def test_position_uses_receive_time_not_pc_clock(
    hass: HomeAssistant, hub, freezer: FrozenDateTimeFactory
) -> None:
    """The position timestamp comes from utcnow(), even if the PC clock is off."""
    now = dt_util.utcnow()
    skewed = _state()
    skewed.timestamp = now - timedelta(minutes=5)

    await _push(hass, hub, skewed)

    attributes = hass.states.get(MEDIA_PLAYER).attributes
    assert attributes["media_position"] == 61
    assert attributes["media_position_updated_at"] == now


async def test_position_timestamp_is_kept_while_paused(
    hass: HomeAssistant, hub
) -> None:
    await _push(hass, hub, _state(isPlaying=False))

    state = hass.states.get(MEDIA_PLAYER)
    assert state.state == MediaPlayerState.PAUSED
    assert state.attributes["media_position_updated_at"] is not None


async def test_media_states(hass: HomeAssistant, hub) -> None:
    await _push(hass, hub, _state())
    assert hass.states.get(MEDIA_PLAYER).state == MediaPlayerState.PLAYING

    paused = _state(isPlaying=False)
    await _push(hass, hub, paused)
    assert hass.states.get(MEDIA_PLAYER).state == MediaPlayerState.PAUSED

    idle = _state()
    idle.track = None
    await _push(hass, hub, idle)
    assert hass.states.get(MEDIA_PLAYER).state == MediaPlayerState.IDLE


async def test_buffering_keeps_playing_state(hass: HomeAssistant, hub) -> None:
    """Short buffering after a track change must not hide the media controls."""
    buffering = _state()
    buffering.is_buffering = True
    await _push(hass, hub, buffering)

    state = hass.states.get(MEDIA_PLAYER)
    assert state.state == MediaPlayerState.PLAYING
    assert state.attributes["is_buffering"] is True


async def test_media_content_id_is_track_uri(hass: HomeAssistant, hub) -> None:
    await _push(hass, hub, _state())

    attributes = hass.states.get(MEDIA_PLAYER).attributes
    assert attributes["media_content_id"] == "spotify:track:abc"
    assert attributes["media_title"] == "Test Track"
    assert attributes["media_duration"] == 180


async def test_no_volume_before_first_state(hass: HomeAssistant, hub) -> None:
    """Before any state arrives, no made-up volume of 100 % is reported."""
    hub.is_connected = True
    hub._notify_connection_update()
    await hass.async_block_till_done()

    state = hass.states.get(MEDIA_PLAYER)
    assert state.state == MediaPlayerState.IDLE
    assert "volume_level" not in state.attributes
