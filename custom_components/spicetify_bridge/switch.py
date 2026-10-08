"""Switch platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    """Set up the Spicetify switch entities."""
    hub = entry.runtime_data
    async_add_entities([SpicetifyLikedTrackSwitch(entry, hub)])


class SpicetifyLikedTrackSwitch(SwitchEntity):
    """Switch to toggle the heart/liked status of the current playing track."""

    _attr_has_entity_name = True
    _attr_translation_key = "liked_track"
    _attr_should_poll = False

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize the liked track switch."""
        self.entry = entry
        self.hub = hub

        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_liked_track"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Spicetify Desktop Client ({port})",
            manufacturer="Spicetify",
            model="Spicetify Connect API",
        )

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
        self.async_write_ha_state()

    @callback
    def _handle_connection_update(self) -> None:
        """Handle connection update signal from hub."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if WebSocket client is connected and a track is active."""
        return self.hub.is_connected and self.hub.current_track is not None

    @property
    def is_on(self) -> bool:
        """Return True if currently playing track is liked/hearted."""
        if not self.hub.player_state:
            return False
        return bool(self.hub.player_state.is_hearted)

    @property
    def icon(self) -> str:
        """Return heart icon depending on liked state."""
        return "mdi:heart" if self.is_on else "mdi:heart-outline"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Heart/Like the current track."""
        await self.hub.async_command(lambda server: server.set_heart(True))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlike/Remove heart from the current track."""
        await self.hub.async_command(lambda server: server.set_heart(False))
