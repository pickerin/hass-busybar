"""HTTP views for the BUSY Bar card."""

from __future__ import annotations

import base64
from http import HTTPStatus

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .api import BusyBarError
from .const import DOMAIN
from .screen import DISPLAYS, decode_frame


class BusyBarScreenView(HomeAssistantView):
    """Serve a decoded display frame for the Lovelace card."""

    url = "/api/busybar/screen/{display}"
    name = "api:busybar:screen"

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def get(self, request: web.Request, display: str) -> web.Response:
        if display not in DISPLAYS:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        entry_id = request.query.get("entry_id")
        entries = [
            e
            for e in self._hass.config_entries.async_entries(DOMAIN)
            if getattr(e, "runtime_data", None)
            and (entry_id is None or e.entry_id == entry_id)
        ]
        if not entries:
            return web.Response(status=HTTPStatus.NOT_FOUND, text="No BUSY Bar loaded")
        api = entries[0].runtime_data.api

        try:
            raw = await api.screen(DISPLAYS[display]["index"])
        except BusyBarError as err:
            return web.Response(status=HTTPStatus.BAD_GATEWAY, text=str(err))

        rgb = decode_frame(raw, display)
        if rgb is None:
            # Firmware's MG_REPLY_IMAGE base64-encodes the framebuffer.
            try:
                rgb = decode_frame(base64.b64decode(raw, validate=True), display)
            except (base64.binascii.Error, ValueError):
                pass
        if rgb is None:
            return web.Response(
                status=HTTPStatus.BAD_GATEWAY, text="Unrecognized frame format"
            )
        return self.json(
            {
                "width": DISPLAYS[display]["width"],
                "height": DISPLAYS[display]["height"],
                "pixels": base64.b64encode(rgb).decode(),
            }
        )
