"""WebSocket listener for the BUSY Bar state stream.

Fires busybar_event on the HA event bus for physical inputs (buttons,
mode switch, encoder wheel) and pushes live timer state into the
coordinator so entities react to on-device changes immediately.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant

from .const import DOMAIN, EVENT_TYPE
from .coordinator import BusyBarCoordinator
from .pb import decode_state

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAY_SECONDS = 10


class BusyBarWsListener:
    """Maintains the status stream connection for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        coordinator: BusyBarCoordinator,
        device_id: str | None,
    ) -> None:
        self._hass = hass
        self._session = session
        self._coordinator = coordinator
        self._device_id = device_id

    async def run(self) -> None:
        """Connect and process the stream forever; reconnect on failure."""
        while True:
            try:
                await self._listen()
            except asyncio.CancelledError:
                raise
            except (aiohttp.ClientError, OSError) as err:
                _LOGGER.debug("State stream disconnected: %s", err)
            except Exception:
                _LOGGER.exception("Unexpected state stream error")
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    async def _listen(self) -> None:
        async with self._session.ws_connect(
            self._coordinator.api.ws_url, heartbeat=25
        ) as ws:
            _LOGGER.debug("State stream connected")
            await ws.send_str(json.dumps({"enable": True}))
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    self._handle_updates(decode_state(msg.data))
                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.ERROR,
                ):
                    break

    def _handle_updates(self, updates: list[dict[str, Any]]) -> None:
        for update in updates:
            if update["type"] == "timer":
                snapshot = update["data"].get("snapshot")
                if snapshot is not None and self._coordinator.data:
                    self._coordinator.async_set_updated_data(
                        {**self._coordinator.data, "snapshot": snapshot}
                    )
            else:
                event = {**update, "device_id": self._device_id}
                _LOGGER.debug("Input event: %s", event)
                self._hass.bus.async_fire(EVENT_TYPE, event)
