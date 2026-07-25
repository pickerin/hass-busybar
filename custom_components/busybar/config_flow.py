"""Config flow for BUSY Bar."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import BusyBarApi, BusyBarAuthError, BusyBarError
from .const import CONF_API_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_API_KEY): str,
    }
)


class BusyBarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle BUSY Bar config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_host: str | None = None
        self._discovered_name: str | None = None

    async def _validate(self, host: str, api_key: str | None) -> tuple[str, str]:
        """Return (unique_id, title) or raise."""
        session = aiohttp_client.async_get_clientsession(self.hass)
        api = BusyBarApi(session, host, api_key)
        await api.version()
        unique_id = host
        try:
            device = await api.status_device()
            unique_id = (
                device.get("serial_number") or device.get("wifi_mac") or host
            )
        except BusyBarError:
            pass
        title = "BUSY Bar"
        try:
            name = await api.name()
            title = name.get("name") or title
        except BusyBarError:
            pass
        return unique_id, title

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            api_key = user_input.get(CONF_API_KEY)
            try:
                unique_id, title = await self._validate(host, api_key)
            except BusyBarAuthError:
                errors["base"] = "invalid_auth"
            except BusyBarError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=title,
                    data={CONF_HOST: host, CONF_API_KEY: api_key},
                )
        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.host
        self._discovered_host = host
        self._discovered_name = discovery_info.name.split(".")[0]
        try:
            unique_id, _ = await self._validate(host, None)
        except BusyBarAuthError:
            # Device requires an API key; let the user enter it manually.
            return await self.async_step_user()
        except BusyBarError:
            return self.async_abort(reason="cannot_connect")
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            _, title = await self._validate(self._discovered_host, None)
            return self.async_create_entry(
                title=title,
                data={CONF_HOST: self._discovered_host, CONF_API_KEY: None},
            )
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": self._discovered_name or "BUSY Bar"},
        )
