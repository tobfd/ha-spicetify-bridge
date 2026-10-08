"""The Spicetify Bridge integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import LOGGER, PLATFORMS
from .hub import SpicetifyBridgeHub

type SpicetifyBridgeConfigEntry = ConfigEntry[SpicetifyBridgeHub]


async def async_setup_entry(
    hass: HomeAssistant, entry: SpicetifyBridgeConfigEntry
) -> bool:
    """Set up Spicetify Bridge from a config entry."""
    LOGGER.debug("Setting up Spicetify Bridge entry: %s", entry.entry_id)

    bridge_hub = SpicetifyBridgeHub(hass, entry)
    await bridge_hub.async_start()

    # Store hub in runtime_data (Modern HA Standard)
    entry.runtime_data = bridge_hub

    # Forward entry setup to platforms. Option changes reload the entry
    # automatically (OptionsFlowWithReload).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SpicetifyBridgeConfigEntry
) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading Spicetify Bridge entry: %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        bridge_hub = entry.runtime_data
        await bridge_hub.async_stop()

    return unload_ok
