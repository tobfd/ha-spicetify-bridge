"""Constants for the Spicetify Bridge integration."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "spicetify_bridge"
LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SENSOR,
]

# Config flow constants
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_API_KEY: Final = "api_key"
CONF_ENABLE_SSL: Final = "enable_ssl"
CONF_CERTFILE: Final = "certfile"
CONF_KEYFILE: Final = "keyfile"

DEFAULT_HOST: Final = "0.0.0.0"
DEFAULT_PORT: Final = 9090
DEFAULT_ENABLE_SSL: Final = True
DEFAULT_CERTFILE: Final = "/ssl/cert.pem"
DEFAULT_KEYFILE: Final = "/ssl/key.pem"

# Dispatcher signals
SIGNAL_SPICETIFY_STATE_UPDATE: Final = "spicetify_bridge_state_update"
SIGNAL_SPICETIFY_CONNECTION_UPDATE: Final = "spicetify_bridge_connection_update"
