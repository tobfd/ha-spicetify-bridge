"""Sensor platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
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
    """Set up the Spicetify sensor entities."""
    hub = entry.runtime_data
    async_add_entities(
        [
            SpicetifyConnectionSensor(entry, hub),
            SpicetifyLatencySensor(entry, hub),
        ]
    )


class SpicetifyConnectionSensor(SensorEntity):
    """Sensor tracking WebSocket connection status with Spicetify."""

    _attr_has_entity_name = True
    _attr_translation_key = "connection_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize connection status sensor."""
        self.hub = hub
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_connection_status"
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
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Handle connection update signal."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> str:
        """Return the connection status."""
        return "connected" if self.hub.is_connected else "disconnected"


class SpicetifyLatencySensor(SensorEntity):
    """Sensor tracking round-trip ping latency to Spicetify client."""

    _attr_has_entity_name = True
    _attr_translation_key = "ping_latency"
    _attr_native_unit_of_measurement = "ms"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize latency sensor."""
        self.hub = hub
        port = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self._attr_unique_id = f"spicetify_bridge_{entry.entry_id}_ping_latency"
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
                self._handle_update,
            )
        )

    @callback
    def _handle_update(self) -> None:
        """Handle connection update signal."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float | None:
        """Return the round-trip latency in milliseconds."""
        if self.hub.last_ping_latency is not None:
            return round(self.hub.last_ping_latency, 2)
        return None
