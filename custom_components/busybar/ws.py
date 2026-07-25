"""WebSocket listener for the BUSY Bar state stream.

Fires busybar_event on the HA event bus for physical inputs (buttons,
mode switch, encoder wheel), forwards them to entities via dispatcher,
tracks connection health, and pushes live timer state into the
coordinator so entities react to on-device changes immediately.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, EVENT_TYPE
from .coordinator import BusyBarCoordinator
from .pb import decode_state

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAY_SECONDS = 10


def signal_input(entry_id: str) -> str:
    """Dispatcher signal for input events."""
    return f"{DOMAIN}_{entry_id}_input"


def signal_connected(entry_id: str) -> str:
    """Dispatcher signal for stream connection state."""
    return f"{DOMAIN}_{entry_id}_connected"


class BusyBarWsListener:
    """Maintains the status stream connection for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: aiohttp.ClientSession,
        coordinator: BusyBarCoordinator,
        entry_id: str,
        device_id: str | None,
    ) -> None:
        self._hass = hass
        self._session = session
        self._coordinator = coordinator
        self._entry_id = entry_id
        self._device_id = device_id
        self.connected = False

    async def run(self) -> None:
        """Connect and process the stream forever; reconnect on failure."""
        while True:
            try:
                await self._listen()
            except asyncio.CancelledError:
                self._set_connected(False)
                raise
            except (aiohttp.ClientError, OSError) as err:
                _LOGGER.debug("State stream disconnected: %s", err)
            except Exception:
                _LOGGER.exception("Unexpected state stream error")
            self._set_connected(False)
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

    def _set_connected(self, connected: bool) -> None:
        if self.connected != connected:
            self.connected = connected
            async_dispatcher_send(
                self._hass, signal_connected(self._entry_id), connected
            )

    async def _listen(self) -> None:
        async with self._session.ws_connect(
            self._coordinator.api.ws_url, heartbeat=25
        ) as ws:
            _LOGGER.debug("State stream connected")
            await ws.send_str(json.dumps({"enable": True}))
            self._set_connected(True)
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
                async_dispatcher_send(
                    self._hass, signal_input(self._entry_id), update
                )
