"""Test that the connection state follows the library's connect/disconnect hooks."""

from unittest.mock import AsyncMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from spicetify import SPOTIFY_DESKTOP_ORIGIN
from spicetify.exceptions import RequestTimeoutError

from custom_components.spicetify_bridge.const import CONF_RESTRICT_ORIGIN

MEDIA_PLAYER = "media_player.spicetify_desktop_client_9090"
CONNECTION_SENSOR = "sensor.spicetify_desktop_client_9090_connection_status"


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_connection_follows_library_hooks(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    await _setup(hass, mock_config_entry)
    assert hass.states.get(MEDIA_PLAYER).state == STATE_UNAVAILABLE

    mock_spotify_server.callbacks["on_connect"]()
    await hass.async_block_till_done()
    assert hass.states.get(CONNECTION_SENSOR).state == "connected"
    assert hass.states.get(MEDIA_PLAYER).state != STATE_UNAVAILABLE

    mock_spotify_server.callbacks["on_disconnect"]()
    await hass.async_block_till_done()
    assert hass.states.get(CONNECTION_SENSOR).state == "disconnected"
    assert hass.states.get(MEDIA_PLAYER).state == STATE_UNAVAILABLE


async def test_failed_ping_does_not_mark_client_offline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """A slow ping must not flip the connection state; only the hooks do that."""
    await _setup(hass, mock_config_entry)
    mock_spotify_server.callbacks["on_connect"]()
    mock_spotify_server.ping.side_effect = RequestTimeoutError("Ping", 5.0)

    assert await mock_config_entry.runtime_data.async_ping_client() is None
    await hass.async_block_till_done()

    assert hass.states.get(CONNECTION_SENSOR).state == "connected"


async def test_origin_restricted_by_default(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    await _setup(hass, mock_config_entry)

    kwargs = mock_spotify_server.server_cls.call_args.kwargs
    assert kwargs["allowed_origins"] == [SPOTIFY_DESKTOP_ORIGIN]


async def test_origin_restriction_can_be_disabled(
    hass: HomeAssistant,
    mock_spotify_server: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    entry = MockConfigEntry(
        domain=mock_config_entry.domain,
        data=dict(mock_config_entry.data),
        options={CONF_RESTRICT_ORIGIN: False},
    )
    await _setup(hass, entry)

    kwargs = mock_spotify_server.server_cls.call_args.kwargs
    assert "allowed_origins" not in kwargs
