"""Hub managing the Spicetify WebSocket server and event dispatching."""

from __future__ import annotations

import ssl
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, TypeVar

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from spicetify import SPOTIFY_DESKTOP_ORIGIN, PlayerState, SpotifyServer
from spicetify.exceptions import (
    NotConnectedError,
    RequestTimeoutError,
    SpicetifyError,
    UnauthorizedError,
)
from websockets.exceptions import ConnectionClosed

from .const import (
    CONF_API_KEY,
    CONF_CERTFILE,
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_KEYFILE,
    CONF_PORT,
    CONF_RESTRICT_ORIGIN,
    DEFAULT_CERTFILE,
    DEFAULT_ENABLE_SSL,
    DEFAULT_HOST,
    DEFAULT_KEYFILE,
    DEFAULT_PORT,
    DEFAULT_RESTRICT_ORIGIN,
    DOMAIN,
    LOGGER,
    SIGNAL_SPICETIFY_CONNECTION_UPDATE,
    SIGNAL_SPICETIFY_STATE_UPDATE,
)

if TYPE_CHECKING:
    from . import SpicetifyBridgeConfigEntry

# Only used to refresh the latency sensor. Connection loss is detected by the
# library (WebSocket keepalive) and reported through on_disconnect.
LATENCY_INTERVAL = timedelta(seconds=60)

_T = TypeVar("_T")


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
        self.restrict_origin: bool = config_data.get(
            CONF_RESTRICT_ORIGIN, DEFAULT_RESTRICT_ORIGIN
        )

        self._server: SpotifyServer | None = None
        self._unsub_latency: CALLBACK_TYPE | None = None

        # State tracking for Home Assistant entities
        self.player_state: PlayerState | None = None
        self.volume_level: float | None = None
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

    def _set_connected(self, connected: bool) -> None:
        """Update the connection state, logging and notifying only on changes."""
        if connected == self.is_connected:
            return
        self.is_connected = connected
        if connected:
            LOGGER.info("Spicetify client connected on port %s", self.port)
        else:
            LOGGER.info("Spicetify client on port %s is unavailable", self.port)
        self._notify_connection_update()

    def _update_player_state(self, state: PlayerState) -> None:
        """Store a new player state snapshot and notify entities."""
        self.player_state = state
        # The library already reports volume as a percentage (0-100).
        self.volume_level = float(state.volume)
        self.position_ms = state.position_ms or 0
        # Use the receive time, not the PC clock (state.timestamp): Home Assistant
        # requires utcnow() here, and the PC clock may drift from Home Assistant.
        self.position_updated_at = dt_util.utcnow()
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

        @server.on_connect
        def handle_connect() -> None:
            self._set_connected(True)
            self._update_device_version(server.client_version)

        @server.on_disconnect
        def handle_disconnect() -> None:
            self._set_connected(False)

    def _update_device_version(self, version: str | None) -> None:
        """Show the connected extension's version on the device page."""
        if not version:
            return
        registry = dr.async_get(self.hass)
        # The entry has exactly one device. (Looked up by config entry because
        # async_get_device is deprecated and its replacement needs HA 2026.10.)
        for device in dr.async_entries_for_config_entry(registry, self.entry.entry_id):
            if device.sw_version != version:
                registry.async_update_device(device.id, sw_version=version)

    async def _async_latency_check(self, _now: datetime) -> None:
        """Periodically refresh the latency sensor while connected."""
        if self.is_connected:
            await self.async_ping_client()

    def _notify_state_update(self) -> None:
        """Dispatch player state update signal to Home Assistant entities."""
        async_dispatcher_send(self.hass, SIGNAL_SPICETIFY_STATE_UPDATE)

    def _notify_connection_update(self) -> None:
        """Dispatch connection update signal to Home Assistant entities."""
        async_dispatcher_send(self.hass, SIGNAL_SPICETIFY_CONNECTION_UPDATE)

    async def async_start(self) -> None:
        """Start the WebSocket server asynchronously.

        Raises:
            ConfigEntryError: If the SSL certificate or key cannot be loaded. The
                user has to fix the files, so retrying would not help.
            ConfigEntryNotReady: If the server cannot be started, for example
                because the port is still in use. Home Assistant retries later.
        """
        LOGGER.info("Starting Spicetify Bridge WebSocket server instance")

        server_kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "api_key": self.api_key,
        }
        if self.restrict_origin:
            # Reject browser pages from other sites (cross-site WebSocket hijacking).
            server_kwargs["allowed_origins"] = [SPOTIFY_DESKTOP_ORIGIN]

        if self.enable_ssl:
            try:
                ssl_ctx = await self.hass.async_add_executor_job(
                    _create_ssl_context, self.certfile, self.keyfile
                )
            except (OSError, ssl.SSLError) as err:
                raise ConfigEntryError(
                    translation_domain=DOMAIN,
                    translation_key="ssl_load_failed",
                    translation_placeholders={
                        "certfile": self.certfile,
                        "keyfile": self.keyfile,
                        "error": str(err),
                    },
                ) from err
            server_kwargs["ssl_context"] = ssl_ctx

        server_instance = SpotifyServer(**server_kwargs)
        self._server = server_instance
        self._register_event_handlers()
        try:
            await server_instance.start()
        except OSError as err:
            self._server = None
            raise ConfigEntryNotReady(
                translation_domain=DOMAIN,
                translation_key="server_start_failed",
                translation_placeholders={
                    "host": self.host,
                    "port": str(self.port),
                    "error": str(err),
                },
            ) from err

        self._unsub_latency = async_track_time_interval(
            self.hass, self._async_latency_check, LATENCY_INTERVAL
        )

    async def async_stop(self) -> None:
        """Stop the WebSocket server asynchronously."""
        LOGGER.info("Stopping Spicetify Bridge WebSocket server instance")

        if self._unsub_latency is not None:
            self._unsub_latency()
            self._unsub_latency = None

        if self._server is not None:
            await self._server.stop()
            self._server = None

        self.player_state = None
        self.volume_level = None
        self.position_ms = None
        self.position_updated_at = None
        self.is_connected = False
        self._notify_connection_update()

    async def async_command(
        self, command: Callable[[SpotifyServer], Awaitable[_T]]
    ) -> _T:
        """Run a command against the Spicetify client and translate failures.

        Service actions must raise ``HomeAssistantError`` on failure so the
        user sees a readable, translated message instead of a stack trace.

        Args:
            command: Callable receiving the server and returning an awaitable.

        Returns:
            The result of the command.

        Raises:
            HomeAssistantError: If the client is offline, does not respond,
                rejects the API key or reports an error.
        """
        if self._server is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            )
        try:
            return await command(self._server)
        except (NotConnectedError, ConnectionClosed) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="not_connected"
            ) from err
        except RequestTimeoutError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="request_timeout",
                translation_placeholders={"command": err.command},
            ) from err
        except UnauthorizedError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="unauthorized"
            ) from err
        except SpicetifyError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="command_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    async def async_ping_client(self) -> float | None:
        """Measure the round-trip latency to the Spicetify client.

        The connection state is not changed here; it comes from the library's
        connect/disconnect hooks.

        Returns:
            The latency in milliseconds, or ``None`` if the ping failed.
        """
        if self._server is None:
            return None
        try:
            latency = await self._server.ping()
        except (SpicetifyError, ConnectionClosed, OSError, TimeoutError) as err:
            LOGGER.debug("Ping request to Spicetify client failed: %s", err)
            return None

        self.last_ping_latency = latency
        # The latency sensor listens to connection updates.
        self._notify_connection_update()
        return latency
