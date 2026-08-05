"""Config flow for Spicetify Bridge integration."""

from __future__ import annotations

import os
import socket
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback

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
    DOMAIN,
)


def _validate_ssl_files(certfile: str, keyfile: str) -> bool:
    """Validate that SSL certificate and key files exist on disk."""
    return os.path.isfile(certfile) and os.path.isfile(keyfile)


def _can_bind_port(host: str, port: int) -> bool:
    """Check if the specified host and port can be bound."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        sock.close()
        return False


class SpicetifyBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Spicetify Bridge."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._config_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input.get(CONF_HOST, DEFAULT_HOST)
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(f"spicetify_bridge_{host}_{port}")
            self._abort_if_unique_id_configured()

            # Verify port availability asynchronously
            can_bind = await self.hass.async_add_executor_job(
                _can_bind_port, host, port
            )
            if not can_bind:
                errors["base"] = "cannot_connect"
            else:
                self._config_data = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_API_KEY: user_input.get(CONF_API_KEY, ""),
                    CONF_ENABLE_SSL: user_input.get(
                        CONF_ENABLE_SSL, DEFAULT_ENABLE_SSL
                    ),
                }

                if self._config_data[CONF_ENABLE_SSL]:
                    return await self.async_step_ssl()

                return self.async_create_entry(
                    title=f"Spicetify Bridge (Port {port})",
                    data=self._config_data,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_API_KEY, default=""): str,
                vol.Required(CONF_ENABLE_SSL, default=DEFAULT_ENABLE_SSL): cv.boolean,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_ssl(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the SSL configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            certfile = user_input[CONF_CERTFILE]
            keyfile = user_input[CONF_KEYFILE]

            files_valid = await self.hass.async_add_executor_job(
                _validate_ssl_files, certfile, keyfile
            )

            if not files_valid:
                errors["base"] = "ssl_file_not_found"
            else:
                self._config_data[CONF_CERTFILE] = certfile
                self._config_data[CONF_KEYFILE] = keyfile

                port = self._config_data[CONF_PORT]
                return self.async_create_entry(
                    title=f"Spicetify Bridge (Port {port})",
                    data=self._config_data,
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CERTFILE, default=DEFAULT_CERTFILE): str,
                vol.Required(CONF_KEYFILE, default=DEFAULT_KEYFILE): str,
            }
        )

        return self.async_show_form(
            step_id="ssl",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow handler."""
        return SpicetifyBridgeOptionsFlow()


class SpicetifyBridgeOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Spicetify Bridge."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the Spicetify Bridge options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            enable_ssl = user_input.get(CONF_ENABLE_SSL, False)
            certfile = user_input.get(CONF_CERTFILE, "")
            keyfile = user_input.get(CONF_KEYFILE, "")

            if enable_ssl:
                files_valid = await self.hass.async_add_executor_job(
                    _validate_ssl_files, certfile, keyfile
                )
                if not files_valid:
                    errors["base"] = "ssl_file_not_found"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        current_data = {**self.config_entry.data, **self.config_entry.options}

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_API_KEY, default=current_data.get(CONF_API_KEY, "")
                ): str,
                vol.Required(
                    CONF_ENABLE_SSL,
                    default=current_data.get(CONF_ENABLE_SSL, DEFAULT_ENABLE_SSL),
                ): cv.boolean,
                vol.Optional(
                    CONF_CERTFILE,
                    default=current_data.get(CONF_CERTFILE, DEFAULT_CERTFILE),
                ): str,
                vol.Optional(
                    CONF_KEYFILE,
                    default=current_data.get(CONF_KEYFILE, DEFAULT_KEYFILE),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
