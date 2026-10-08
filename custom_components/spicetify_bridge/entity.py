"""Base entity for the Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

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


class SpicetifyEntity(Entity):
    """Common base for all Spicetify Bridge entities.

    Provides the shared device, the unique ID scheme and push updates from the hub.
    """

    _attr_has_entity_name = True
    _attr_should_poll = False

    #: Whether the entity also refreshes on player state updates (not only on
    #: connection updates).
    _listens_to_player_state = False

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub, key: str
    ) -> None:
        """Initialize the entity.

        Args:
            entry: The config entry the entity belongs to.
            hub: The hub providing state and commands.
            key: Entity key used to build the (unchanged) unique ID.
        """
        self.hub = hub
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Spicetify Desktop Client ({port})",
            manufacturer="Spicetify",
            model="Spicetify Connect API",
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to hub updates when the entity is added."""
        await super().async_added_to_hass()
        signals = [SIGNAL_SPICETIFY_CONNECTION_UPDATE]
        if self._listens_to_player_state:
            signals.append(SIGNAL_SPICETIFY_STATE_UPDATE)
        for signal in signals:
            self.async_on_remove(
                async_dispatcher_connect(self.hass, signal, self._handle_hub_update)
            )

    @callback
    def _handle_hub_update(self) -> None:
        """Write the new state when the hub reports a change."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the Spicetify client is connected."""
        return self.hub.is_connected
