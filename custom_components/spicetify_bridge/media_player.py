"""Media Player platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.components.media_player import (
    RepeatMode as HARepeatMode,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from spicetify import RepeatMode as SpicetifyRepeatMode

from .const import (
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    SIGNAL_SPICETIFY_CONNECTION_UPDATE,
    SIGNAL_SPICETIFY_STATE_UPDATE,
)

if TYPE_CHECKING:
    from . import SpicetifyBridgeConfigEntry
    from .hub import SpicetifyBridgeHub


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SpicetifyBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Spicetify media player entity."""
    hub = entry.runtime_data
    async_add_entities([SpicetifyMediaPlayer(entry, hub)])


class SpicetifyMediaPlayer(MediaPlayerEntity):
    """Representation of a Spicetify Desktop Client media player."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize the media player entity."""
        self.entry = entry
        self.hub = hub

        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_media_player"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Spicetify Desktop Client ({port})",
            manufacturer="Spicetify",
            model="Spicetify Connect API",
        )
        self._is_muted: bool = False

    async def async_added_to_hass(self) -> None:
        """Register callbacks when entity is added to Home Assistant."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_SPICETIFY_STATE_UPDATE,
                self._handle_state_update,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_SPICETIFY_CONNECTION_UPDATE,
                self._handle_connection_update,
            )
        )

    @callback
    def _handle_state_update(self) -> None:
        """Handle state update signal from hub."""
        state = self.hub.player_state
        if state and getattr(state, "is_muted", None) is not None:
            self._is_muted = state.is_muted
        self.async_write_ha_state()

    @callback
    def _handle_connection_update(self) -> None:
        """Handle connection update signal from hub."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the Spicetify WebSocket client is connected."""
        return self.hub.is_connected

    @property
    def state(self) -> MediaPlayerState:
        """Return the current playback state of the player."""
        if not self.hub.is_connected:
            return MediaPlayerState.OFF
        if self.hub.player_state and self.hub.player_state.is_playing:
            return MediaPlayerState.PLAYING
        return MediaPlayerState.PAUSED

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features dynamically based on SpotifyRestrictions."""
        features = (
            MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
        )

        state = self.hub.player_state
        if not state or not state.restrictions:
            return (
                features
                | MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.NEXT_TRACK
                | MediaPlayerEntityFeature.PREVIOUS_TRACK
                | MediaPlayerEntityFeature.SEEK
                | MediaPlayerEntityFeature.REPEAT_SET
                | MediaPlayerEntityFeature.SHUFFLE_SET
            )

        r = state.restrictions
        if r.can_pause or r.can_resume:
            features |= MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE
        if r.can_skip_next:
            features |= MediaPlayerEntityFeature.NEXT_TRACK
        if r.can_skip_previous:
            features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
        if r.can_seek:
            features |= MediaPlayerEntityFeature.SEEK
        if r.can_toggle_repeat_context or r.can_toggle_repeat_track:
            features |= MediaPlayerEntityFeature.REPEAT_SET
        if r.can_toggle_shuffle or r.can_toggle_smart_shuffle:
            features |= MediaPlayerEntityFeature.SHUFFLE_SET

        return features

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0.0 to 1.0)."""
        return self.hub.volume_level / 100.0

    @property
    def is_volume_muted(self) -> bool | None:
        """Return True if volume is muted."""
        state = self.hub.player_state
        if state and getattr(state, "is_muted", None) is not None:
            return state.is_muted
        return self._is_muted

    @property
    def media_content_type(self) -> MediaType:
        """Content type of current playing media."""
        return MediaType.MUSIC

    @property
    def media_title(self) -> str | None:
        """Title of current playing track."""
        track = self.hub.current_track
        return track.title if track else None

    @property
    def media_artist(self) -> str | None:
        """Artist(s) of current playing track."""
        track = self.hub.current_track
        if track and track.artists:
            return ", ".join(artist.name for artist in track.artists)
        return None

    @property
    def media_album_name(self) -> str | None:
        """Album name of current playing track."""
        track = self.hub.current_track
        if track and track.album:
            return track.album.name
        return None

    @property
    def media_image_url(self) -> str | None:
        """Album artwork URL of current playing track."""
        track = self.hub.current_track
        if not track:
            return None
        if hasattr(track, "images") and track.images and track.images.large:
            return track.images.large
        return track.image_url

    @property
    def media_duration(self) -> int | None:
        """Duration of current playing track in seconds."""
        track = self.hub.current_track
        if track and track.duration_ms:
            return int(track.duration_ms // 1000)
        if self.hub.player_state and self.hub.player_state.duration_ms:
            return int(self.hub.player_state.duration_ms // 1000)
        return None

    @property
    def media_position(self) -> int | None:
        """Position of current playing track in seconds."""
        if self.hub.position_ms is not None:
            return int(self.hub.position_ms // 1000)
        return None

    @property
    def media_position_updated_at(self) -> dt_util.dt.datetime | None:
        """When position was last updated."""
        if self.state == MediaPlayerState.PLAYING and self.hub.position_updated_at:
            return self.hub.position_updated_at
        return None

    @property
    def is_favorite(self) -> bool | None:
        """Return True if current playing track is liked/hearted."""
        if not self.hub.player_state:
            return None
        return self.hub.player_state.is_hearted

    @property
    def shuffle(self) -> bool | None:
        """Return True if shuffle mode is enabled."""
        return self.hub.player_state.shuffle if self.hub.player_state else None

    @property
    def repeat(self) -> HARepeatMode | None:
        """Return current repeat mode."""
        if not self.hub.player_state:
            return None

        mode = self.hub.player_state.repeat_mode
        if mode == SpicetifyRepeatMode.TRACK:
            return HARepeatMode.ONE
        if mode == SpicetifyRepeatMode.CONTEXT:
            return HARepeatMode.ALL
        return HARepeatMode.OFF

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return rich metadata attributes from Spicetify PlayerState."""
        attrs: dict[str, Any] = {}
        state = self.hub.player_state
        if not state:
            return attrs

        if state.context:
            attrs["context_uri"] = state.context.uri
            attrs["context_description"] = state.context.description
            attrs["context_owner"] = state.context.owner

        if state.item_index is not None:
            attrs["playlist_track_number"] = state.item_index + 1

        attrs["is_buffering"] = state.is_buffering

        track = state.track
        if track:
            if track.popularity is not None:
                attrs["popularity"] = track.popularity
            if track.has_lyrics is not None:
                attrs["has_lyrics"] = track.has_lyrics

        return attrs

    # Media Control Commands
    async def async_media_play(self) -> None:
        """Send play command."""
        await self.hub.server.play()

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self.hub.server.pause()

    async def async_media_stop(self) -> None:
        """Send stop command (pauses playback)."""
        await self.hub.server.pause()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self.hub.server.next_song()

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        await self.hub.server.previous_song(force=False)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level (0.0 to 1.0)."""
        percent = volume * 100.0
        await self.hub.server.set_volume(percent)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute playback."""
        await self.hub.server.set_mute(mute)
        self._is_muted = mute
        self.async_write_ha_state()

    async def async_media_seek(self, position: float) -> None:
        """Seek to position in seconds."""
        position_ms = position * 1000.0
        await self.hub.server.seek(position_ms)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable or disable shuffle mode."""
        await self.hub.server.set_shuffle(shuffle)

    async def async_set_repeat(self, repeat: HARepeatMode) -> None:
        """Set repeat mode."""
        if repeat == HARepeatMode.ONE:
            mode = SpicetifyRepeatMode.TRACK
        elif repeat == HARepeatMode.ALL:
            mode = SpicetifyRepeatMode.CONTEXT
        else:
            mode = SpicetifyRepeatMode.OFF
        await self.hub.server.set_repeat(mode)

    async def async_set_favorite(self, favorite: bool) -> None:
        """Like or unlike the currently playing track."""
        await self.hub.server.set_heart(favorite)

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs: Any
    ) -> None:
        """Play media via Spotify URI or URL."""
        await self.hub.server.play_uri(media_id)
