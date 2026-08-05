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
    _enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integrations in Home Assistant test environment."""
    yield


@pytest.fixture
def mock_spotify_server() -> Generator[AsyncMock, None, None]:
    """Mock the SpotifyServer instance from spicetify-websocket (v0.3.0)."""
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

        # Mock Decorator Registration Handlers
        def dummy_decorator(func):
            return func

        mock_instance.on_state_changed = dummy_decorator
        mock_instance.on_ping = dummy_decorator
        mock_instance.on_heart_changed = dummy_decorator

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
        unique_id="spicetify_bridge_9090",
    )
