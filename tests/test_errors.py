"""Test error handling: translated service errors and setup failures."""

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
)
from homeassistant.components.media_player import (
    SERVICE_MEDIA_PLAY,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry
from spicetify.exceptions import (
    NotConnectedError,
    RequestTimeoutError,
    SpicetifyError,
    UnauthorizedError,
)

from custom_components.spicetify_bridge.const import (
    CONF_CERTFILE,
    CONF_ENABLE_SSL,
    CONF_HOST,
    CONF_KEYFILE,
    CONF_PORT,
    DOMAIN,
)

MEDIA_PLAYER = "media_player.spicetify_desktop_client_9090"


async def _setup_connected(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hub = entry.runtime_data
    hub.is_connected = True
    hub._notify_connection_update()
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("error", "translation_key"),
    [
        (NotConnectedError(), "not_connected"),
        (RequestTimeoutError("Play", 5.0), "request_timeout"),
        (UnauthorizedError(), "unauthorized"),
        (SpicetifyError("Request failed: boom"), "command_failed"),
    ],
)
async def test_service_errors_are_translated(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
    error: Exception,
    translation_key: str,
) -> None:
    """Library errors surface as translated HomeAssistantError, not stack traces."""
    await _setup_connected(hass, mock_config_entry)
    mock_spotify_server.play.side_effect = error

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_MEDIA_PLAY,
            {ATTR_ENTITY_ID: MEDIA_PLAYER},
            blocking=True,
        )

    assert exc_info.value.translation_domain == DOMAIN
    assert exc_info.value.translation_key == translation_key


async def test_ping_button_raises_when_client_offline(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """Pressing the ping button while the client is offline reports an error."""
    await _setup_connected(hass, mock_config_entry)
    mock_spotify_server.ping.side_effect = NotConnectedError()

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            "button",
            "press",
            {ATTR_ENTITY_ID: "button.spicetify_desktop_client_9090_ping_client"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "not_connected"
    assert mock_config_entry.runtime_data.is_connected is False


async def test_setup_retries_when_port_is_busy(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
) -> None:
    """A port that is still in use leads to a setup retry instead of a hard error."""
    mock_spotify_server.start.side_effect = OSError(98, "Address already in use")
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_fails_when_certificate_is_missing(
    hass: HomeAssistant,
    mock_spotify_server: AsyncMock,
) -> None:
    """Missing certificate files need user action, so setup fails without retry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "0.0.0.0",
            CONF_PORT: 9090,
            CONF_ENABLE_SSL: True,
            CONF_CERTFILE: "/does/not/exist/cert.pem",
            CONF_KEYFILE: "/does/not/exist/key.pem",
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    mock_spotify_server.start.assert_not_called()


async def test_connection_changes_are_logged_once(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_spotify_server: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unavailability and recovery are logged once each at INFO level."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    hub = mock_config_entry.runtime_data
    caplog.set_level(logging.INFO, logger="custom_components.spicetify_bridge")

    with patch.object(hub, "_notify_connection_update"):
        hub._set_connected(True)
        hub._set_connected(True)
        hub._set_connected(False)
        hub._set_connected(False)

    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert sum("connected on port" in m for m in messages) == 1
    assert sum("is unavailable" in m for m in messages) == 1
