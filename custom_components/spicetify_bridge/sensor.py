"""Sensor platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import SpicetifyEntity

if TYPE_CHECKING:
    from . import SpicetifyBridgeConfigEntry
    from .hub import SpicetifyBridgeHub

# Read-only platform, updated by push from the hub.
PARALLEL_UPDATES = 0


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


class SpicetifyConnectionSensor(SpicetifyEntity, SensorEntity):
    """Sensor tracking WebSocket connection status with Spicetify."""

    _attr_translation_key = "connection_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize connection status sensor."""
        super().__init__(entry, hub, "connection_status")
        self._attr_options = ["connected", "disconnected"]

    @property
    def available(self) -> bool:
        """The connection status is always known, even while disconnected."""
        return True

    @property
    def native_value(self) -> str:
        """Return the connection status."""
        return "connected" if self.hub.is_connected else "disconnected"


class SpicetifyLatencySensor(SpicetifyEntity, SensorEntity):
    """Sensor tracking round-trip ping latency to Spicetify client."""

    _attr_translation_key = "ping_latency"
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    # Updated every heartbeat; only useful for troubleshooting.
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize latency sensor."""
        super().__init__(entry, hub, "ping_latency")

    @property
    def native_value(self) -> float | None:
        """Return the round-trip latency in milliseconds."""
        if self.hub.last_ping_latency is None:
            return None
        return round(self.hub.last_ping_latency, 2)
