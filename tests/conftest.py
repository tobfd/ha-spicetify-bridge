"""Global fixtures for Spicetify Bridge integration tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.spicetify_bridge.const import (
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
)

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integrations in Home Assistant test environment."""
    _ = enable_custom_integrations
    yield


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Prevent config flow tests from setting up the entry (and binding a real port)."""
    with patch(
        "custom_components.spicetify_bridge.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


@pytest.fixture
def mock_spotify_server() -> Generator[AsyncMock, None, None]:
    """Mock the SpotifyServer instance from spicetify-websocket."""
    with patch(
        "custom_components.spicetify_bridge.hub.SpotifyServer"
    ) as mock_server_cls:
        mock_instance = AsyncMock()
        mock_server_cls.return_value = mock_instance

        # Server Lifecycles & Async Commands
        mock_instance.start = AsyncMock()
        mock_instance.stop = AsyncMock()
        mock_instance.ping = AsyncMock(return_value=12.5)
        mock_instance.play = AsyncMock()
        mock_instance.pause = AsyncMock()
        mock_instance.next_song = AsyncMock()
        mock_instance.previous_song = AsyncMock()
        mock_instance.set_volume = AsyncMock()
        mock_instance.set_mute = AsyncMock()
        mock_instance.seek = AsyncMock()
        mock_instance.set_shuffle = AsyncMock()
        mock_instance.set_repeat = AsyncMock()
        mock_instance.set_heart = AsyncMock(return_value=True)
        mock_instance.toggle_heart = AsyncMock(return_value=True)
        mock_instance.play_uri = AsyncMock(return_value="spotify:track:test")

        # Record decorator registrations so tests can trigger the callbacks.
        mock_instance.callbacks = {}

        def recorder(name):
            def decorator(func):
                mock_instance.callbacks[name] = func
                return func

            return decorator

        for name in ("on_state_changed", "on_ping", "on_connect", "on_disconnect"):
            setattr(mock_instance, name, recorder(name))

        mock_instance.server_cls = mock_server_cls
        yield mock_instance


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry for Spicetify Bridge."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Spicetify Bridge (Port 9090)",
        data={
            CONF_HOST: "0.0.0.0",
            CONF_PORT: 9090,
            CONF_ENABLE_SSL: False,
        },
        entry_id="spicetify_bridge_test_entry",
    )
