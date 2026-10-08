"""Switch platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SpicetifyEntity

if TYPE_CHECKING:
    from . import SpicetifyBridgeConfigEntry
    from .hub import SpicetifyBridgeHub

# Commands go to a single Spotify client, so send them one at a time.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SpicetifyBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Spicetify switch entities."""
    hub = entry.runtime_data
    async_add_entities([SpicetifyLikedTrackSwitch(entry, hub)])


class SpicetifyLikedTrackSwitch(SpicetifyEntity, SwitchEntity):
    """Switch to toggle the heart/liked status of the current playing track."""

    _attr_translation_key = "liked_track"
    _listens_to_player_state = True

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize the liked track switch."""
        super().__init__(entry, hub, "liked_track")

    @property
    def available(self) -> bool:
        """Return True if the client is connected and a track is loaded."""
        return super().available and self.hub.current_track is not None

    @property
    def is_on(self) -> bool:
        """Return True if currently playing track is liked/hearted."""
        state = self.hub.player_state
        return bool(state and state.is_hearted)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Heart/Like the current track."""
        await self.hub.async_command(lambda server: server.set_heart(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlike/Remove heart from the current track."""
        await self.hub.async_command(lambda server: server.set_heart(False))
