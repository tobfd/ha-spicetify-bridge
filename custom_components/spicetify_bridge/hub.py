"""Hub managing the Spicetify WebSocket server and event dispatching."""

from __future__ import annotations

import ssl
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from spicetify import PlayerState, SpotifyServer
from spicetify.exceptions import SpicetifyError

from .const import (
    CONF_API_KEY,
    CONF_CERTFILE,
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_KEYFILE,
    CONF_PORT,
    DEFAULT_CERTFILE,
    DEFAULT_ENABLE_SSL,
    DEFAULT_HOST,
    DEFAULT_KEYFILE,
    DEFAULT_PORT,
    LOGGER,
    SIGNAL_SPICETIFY_CONNECTION_UPDATE,
    SIGNAL_SPICETIFY_STATE_UPDATE,
)

if TYPE_CHECKING:
    from . import SpicetifyBridgeConfigEntry

HEARTBEAT_INTERVAL = timedelta(seconds=15)


def _create_ssl_context(certfile: str, keyfile: str) -> ssl.SSLContext:
    """Create SSL context in an executor thread to prevent blocking event loop."""
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return ssl_ctx


class SpicetifyBridgeHub:
    """Hub to interface Home Assistant with the spicetify-websocket server."""

    def __init__(self, hass: HomeAssistant, entry: SpicetifyBridgeConfigEntry) -> None:
        """Initialize the hub instance."""
        self.hass = hass
        self.entry = entry

        config_data = {**entry.data, **entry.options}

        self.host: str = config_data.get(CONF_HOST, DEFAULT_HOST)
        self.port: int = config_data.get(CONF_PORT, DEFAULT_PORT)
        self.api_key: str | None = config_data.get(CONF_API_KEY) or None
        self.enable_ssl: bool = config_data.get(CONF_ENABLE_SSL, DEFAULT_ENABLE_SSL)
        self.certfile: str = config_data.get(CONF_CERTFILE, DEFAULT_CERTFILE)
        self.keyfile: str = config_data.get(CONF_KEYFILE, DEFAULT_KEYFILE)

        self._server: SpotifyServer | None = None
        self._unsub_heartbeat: CALLBACK_TYPE | None = None

        # State tracking for Home Assistant entities
        self.player_state: PlayerState | None = None
        self.volume_level: float = 100.0
        self.is_connected: bool = False
        self.last_ping_latency: float | None = None
        self.last_heartbeat: datetime | None = None

        # Position Tracking
        self.position_ms: int | None = None
        self.position_updated_at: datetime | None = None

    @property
    def server(self) -> SpotifyServer:
        """Return the active SpotifyServer instance, raising error if not started."""
        if self._server is None:
            raise RuntimeError("Spicetify Bridge server is not initialized yet")
        return self._server

    @property
    def current_track(self):
        """Return current track info from player state."""
        return self.player_state.track if self.player_state else None

    def _update_player_state(self, state: PlayerState) -> None:
        """Central update handler utilizing state.timestamp for precision synchronization."""
        now = dt_util.utcnow()
        self.player_state = state

        if isinstance(state.volume, (float, int)):
            self.volume_level = (
                state.volume * 100.0 if state.volume <= 1.0 else float(state.volume)
            )

        self.position_ms = state.position_ms or 0

        if state.is_playing:
            event_time: datetime = (
                state.timestamp if isinstance(state.timestamp, datetime) else now
            )
            # Cap event_time to 'now' to prevent future-timestamp drift if PC clock is ahead
            self.position_updated_at = min(event_time, now)
        else:
            self.position_updated_at = None

        if not self.is_connected:
            self.is_connected = True
            self._notify_connection_update()

        self._notify_state_update()

    def _register_event_handlers(self) -> None:
        """Register callbacks with SpotifyServer push events."""
        server = self.server

        @server.on_state_changed
        def handle_state_changed(state: PlayerState) -> None:
            LOGGER.debug(
                "Received Spicetify state update [%s]: playing=%s, pos_ms=%s",
                state.event_name,
                state.is_playing,
                state.position_ms,
            )
            self._update_player_state(state)

        @server.on_ping
        def handle_ping(ping_time: datetime) -> None:
            LOGGER.debug("Received Heartbeat Ping at: %s", ping_time)
            self.last_heartbeat = ping_time
            if not self.is_connected:
                self.is_connected = True
                self._notify_connection_update()

    async def _async_heartbeat_check(self, _now: datetime) -> None:
        """Periodically ping client to detect ungraceful disconnections."""
        if self.is_connected:
            await self.async_ping_client()

    def _notify_state_update(self) -> None:
        """Dispatch player state update signal to Home Assistant entities."""
        async_dispatcher_send(self.hass, SIGNAL_SPICETIFY_STATE_UPDATE)

    def _notify_connection_update(self) -> None:
        """Dispatch connection update signal to Home Assistant entities."""
        async_dispatcher_send(self.hass, SIGNAL_SPICETIFY_CONNECTION_UPDATE)

    async def async_start(self) -> None:
        """Start the WebSocket server asynchronously."""
        LOGGER.info("Starting Spicetify Bridge WebSocket server instance")

        server_kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "api_key": self.api_key,
        }

        if self.enable_ssl:
            ssl_ctx = await self.hass.async_add_executor_job(
                _create_ssl_context, self.certfile, self.keyfile
            )
            server_kwargs["ssl_context"] = ssl_ctx

        server_instance = SpotifyServer(**server_kwargs)
        self._server = server_instance
        self._register_event_handlers()
        await server_instance.start()

        self._unsub_heartbeat = async_track_time_interval(
            self.hass, self._async_heartbeat_check, HEARTBEAT_INTERVAL
        )

    async def async_stop(self) -> None:
        """Stop the WebSocket server asynchronously."""
        LOGGER.info("Stopping Spicetify Bridge WebSocket server instance")

        if self._unsub_heartbeat is not None:
            self._unsub_heartbeat()
            self._unsub_heartbeat = None

        if self._server is not None:
            await self._server.stop()
            self._server = None

        self.player_state = None
        self.position_ms = None
        self.position_updated_at = None
        self.is_connected = False
        self._notify_connection_update()

    async def async_ping_client(self) -> float | None:
        """Trigger a manual ping request to the Spicetify client."""
        if self._server is None:
            return None
        try:
            latency = await self.server.ping()
            self.last_ping_latency = latency
            self.is_connected = True
            self._notify_connection_update()
            return latency
        except (SpicetifyError, OSError, TimeoutError) as err:
            LOGGER.debug(
                "Ping request to Spicetify client failed (client offline): %s", err
            )
            if self.is_connected:
                self.is_connected = False
                self._notify_connection_update()
            return None
        except Exception as err:  # noqa: BLE001
            LOGGER.error("Unexpected error during ping request: %s", err)
            if self.is_connected:
                self.is_connected = False
                self._notify_connection_update()
            return None
