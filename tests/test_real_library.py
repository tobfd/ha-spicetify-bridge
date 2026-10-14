"""Integration tests with the real spicetify-websocket library.

The other tests replace the library with a mock. These tests start the real
WebSocket server on a free local port and connect a client that speaks the
extension's protocol (see PROTOCOL.md in spicetify-connect-api), so a change in
the library or the protocol that breaks the integration fails here.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest
from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.components.media_player import (
    SERVICE_MEDIA_PAUSE,
    SERVICE_VOLUME_SET,
    MediaPlayerState,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry
from spicetify import SPOTIFY_DESKTOP_ORIGIN
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import InvalidStatus

from custom_components.spicetify_bridge.const import (
    CONF_API_KEY,
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
)

# These tests open real (local) sockets, which Home Assistant's test plugin blocks by default.
pytestmark = pytest.mark.usefixtures("socket_enabled")

API_KEY = "real-library-secret"
MEDIA_PLAYER = "media_player.spicetify_desktop_client_0"
CONNECTION_SENSOR = "sensor.spicetify_desktop_client_0_connection_status"

PLAYER_DATA = {
    "timestamp": 1791499175054,
    "positionAsOfTimestamp": 61000,
    "duration": 188453,
    "isPaused": False,
    "isBuffering": False,
    "shuffle": False,
    "repeat": 0,
    "hasContext": True,
    "item": {
        "uri": "spotify:track:0laYHRpNTS6i8FXdupHkJ4",
        "name": "Love You Like A Love Song",
        "artists": [
            {"name": "Selena Gomez & The Scene", "uri": "spotify:artist:6dJeK"}
        ],
        "album": {"name": "When The Sun Goes Down", "uri": "spotify:album:4d6"},
        "duration": {"milliseconds": 188453},
        "metadata": {},
    },
    "context": {"uri": "spotify:playlist:37i9", "metadata": {}},
    "restrictions": {},
    "nextItems": [],
    "previousItems": [],
}


def _state_payload(**extra: Any) -> dict[str, Any]:
    return {
        "playerData": PLAYER_DATA,
        "isPlaying": True,
        "volume": 0.42,
        "isMuted": False,
        "isHearted": True,
        "shuffle": False,
        "repeat": 0,
        "progress": 61000,
        **extra,
    }


class FakeExtension:
    """A WebSocket client that behaves like spicetify-connect-api 0.4.0."""

    def __init__(self, ws: ClientConnection) -> None:
        self.ws = ws
        self.requests: list[dict[str, Any]] = []
        self.fail_with: dict[str, str] | None = None
        self._task = asyncio.create_task(self._answer())

    async def _answer(self) -> None:
        async for raw in self.ws:
            request = json.loads(raw)
            self.requests.append(request)
            response: dict[str, Any] = {
                "eventName": "Response",
                "requestId": request["requestId"],
                "success": True,
                "payload": {},
                "token": API_KEY,
            }
            if self.fail_with is not None:
                response.update(success=False, **self.fail_with)
            await self.ws.send(json.dumps(response))

    async def close(self) -> None:
        await self.ws.close()
        await self._task


async def _wait_until(condition: Callable[[], bool], timeout: float = 3.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition():
        if loop.time() > deadline:
            raise AssertionError("Condition was not met in time")
        await asyncio.sleep(0.01)


@pytest.fixture
async def entry(hass: HomeAssistant) -> AsyncIterator[MockConfigEntry]:
    """A config entry running the real server on a free local port."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "127.0.0.1",
            CONF_PORT: 0,
            CONF_ENABLE_SSL: False,
            CONF_API_KEY: API_KEY,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


def _url(entry: MockConfigEntry) -> str:
    server = entry.runtime_data.server.server
    return f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"


@pytest.fixture
async def extension(
    hass: HomeAssistant, entry: MockConfigEntry
) -> AsyncIterator[FakeExtension]:
    """A connected and authenticated fake extension."""
    ws = await connect(_url(entry), origin=SPOTIFY_DESKTOP_ORIGIN)
    initial = {
        "eventName": "InitialState",
        "token": API_KEY,
        "payload": _state_payload(protocolVersion=1, extensionVersion="0.4.0"),
    }
    await ws.send(json.dumps(initial))
    client = FakeExtension(ws)
    await _wait_until(lambda: entry.runtime_data.is_connected)
    await hass.async_block_till_done()
    yield client
    await client.close()


async def test_state_from_real_client(
    hass: HomeAssistant, entry: MockConfigEntry, extension: FakeExtension
) -> None:
    """The InitialState of a real connection ends up in the entities."""
    state = hass.states.get(MEDIA_PLAYER)
    assert state.state == MediaPlayerState.PLAYING
    assert state.attributes["media_title"] == "Love You Like A Love Song"
    assert state.attributes["media_artist"] == "Selena Gomez & The Scene"
    assert state.attributes["volume_level"] == 0.42
    assert state.attributes["media_position"] == 61
    assert hass.states.get(CONNECTION_SENSOR).state == "connected"


async def test_extension_version_on_device(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    entry: MockConfigEntry,
    extension: FakeExtension,
) -> None:
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert [device.sw_version for device in devices] == ["0.4.0"]


async def test_service_calls_reach_the_client(
    hass: HomeAssistant, entry: MockConfigEntry, extension: FakeExtension
) -> None:
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_PAUSE,
        {ATTR_ENTITY_ID: MEDIA_PLAYER},
        blocking=True,
    )
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {ATTR_ENTITY_ID: MEDIA_PLAYER, "volume_level": 0.5},
        blocking=True,
    )

    names = [(r["requestName"], r.get("payload")) for r in extension.requests]
    assert ("Pause", {}) in names or ("Pause", None) in names
    assert ("SetVolume", {"level": 0.5}) in names
    assert all(r["token"] == API_KEY for r in extension.requests)


async def test_client_errors_become_translated_errors(
    hass: HomeAssistant, entry: MockConfigEntry, extension: FakeExtension
) -> None:
    extension.fail_with = {"error": "Track unavailable", "code": "command_failed"}

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_MEDIA_PAUSE,
            {ATTR_ENTITY_ID: MEDIA_PLAYER},
            blocking=True,
        )
    assert exc_info.value.translation_key == "command_failed"


async def test_push_events_update_the_state(
    hass: HomeAssistant, entry: MockConfigEntry, extension: FakeExtension
) -> None:
    event = {
        "eventName": "PlayPauseChanged",
        "token": API_KEY,
        "payload": _state_payload(isPlaying=False),
    }
    await extension.ws.send(json.dumps(event))
    await _wait_until(
        lambda: hass.states.get(MEDIA_PLAYER).state == MediaPlayerState.PAUSED
    )


async def test_disconnect_makes_entities_unavailable(
    hass: HomeAssistant, entry: MockConfigEntry, extension: FakeExtension
) -> None:
    await extension.close()
    await _wait_until(lambda: not entry.runtime_data.is_connected)
    await hass.async_block_till_done()

    assert hass.states.get(MEDIA_PLAYER).state == STATE_UNAVAILABLE
    assert hass.states.get(CONNECTION_SENSOR).state == "disconnected"


async def test_foreign_origin_is_rejected(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """With the default origin restriction, other web pages cannot connect."""
    with pytest.raises(InvalidStatus):
        await connect(_url(entry), origin="https://evil.example")
    assert not entry.runtime_data.is_connected


async def test_wrong_api_key_is_rejected(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    async with connect(_url(entry), origin=SPOTIFY_DESKTOP_ORIGIN) as ws:
        initial = {
            "eventName": "InitialState",
            "token": "wrong",
            "payload": _state_payload(),
        }
        await ws.send(json.dumps(initial))
        await asyncio.sleep(0.2)
        assert not entry.runtime_data.is_connected
