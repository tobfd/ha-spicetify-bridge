"""Button platform for Spicetify Bridge integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
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
    """Set up the Spicetify button entities."""
    hub = entry.runtime_data
    async_add_entities(
        [
            SpicetifyForcePreviousButton(entry, hub),
            SpicetifyPingButton(entry, hub),
        ]
    )


class SpicetifyForcePreviousButton(SpicetifyEntity, ButtonEntity):
    """Button to force skip to the previous track regardless of elapsed time."""

    _attr_translation_key = "force_previous"

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize force previous button."""
        super().__init__(entry, hub, "force_previous")

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hub.async_command(lambda server: server.previous_song(force=True))


class SpicetifyPingButton(SpicetifyEntity, ButtonEntity):
    """Button to trigger a manual latency ping to the Spicetify client."""

    _attr_translation_key = "ping_client"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, entry: SpicetifyBridgeConfigEntry, hub: SpicetifyBridgeHub
    ) -> None:
        """Initialize ping button."""
        super().__init__(entry, hub, "ping_client")

    async def async_press(self) -> None:
        """Handle the button press."""
        if await self.hub.async_ping_client() is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            )
