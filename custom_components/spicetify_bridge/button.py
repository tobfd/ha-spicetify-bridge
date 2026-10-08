"""Button platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    SIGNAL_SPICETIFY_CONNECTION_UPDATE,
)

if TYPE_CHECKING:
    from . import SpicetifyBridgeConfigEntry
    from .hub import SpicetifyBridgeHub


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: SpicetifyBridgeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Spicetify button entities."""
    hub = entry.runtime_data
    async_add_entities(
        [
            SpicetifyForcePreviousButton(entry, hub),
            SpicetifyPingButton(entry, hub),
        ]
    )


class SpicetifyForcePreviousButton(ButtonEntity):
    """Button to force skip to the previous track regardless of elapsed time."""

    _attr_has_entity_name = True
    _attr_translation_key = "force_previous"

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize force previous button."""
        self.hub = hub
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_force_previous"
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
                SIGNAL_SPICETIFY_CONNECTION_UPDATE,
                self._handle_connection_update,
            )
        )

    @callback
    def _handle_connection_update(self) -> None:
        """Handle connection update signal from hub."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if WebSocket client is connected."""
        return self.hub.is_connected

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hub.async_command(lambda server: server.previous_song(force=True))


class SpicetifyPingButton(ButtonEntity):
    """Button to trigger a manual latency ping to the Spicetify client."""

    _attr_has_entity_name = True
    _attr_translation_key = "ping_client"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize ping button."""
        self.hub = hub
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_ping_client"
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
                SIGNAL_SPICETIFY_CONNECTION_UPDATE,
                self._handle_connection_update,
            )
        )

    @callback
    def _handle_connection_update(self) -> None:
        """Handle connection update signal from hub."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if WebSocket client is connected."""
        return self.hub.is_connected

    async def async_press(self) -> None:
        """Handle the button press."""
        if await self.hub.async_ping_client() is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            )
