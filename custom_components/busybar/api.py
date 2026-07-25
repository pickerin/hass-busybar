"""Minimal async client for the BUSY Bar local HTTP API.

Endpoint shapes mirror the official busylib-py SDK
(https://github.com/busy-app/busylib-py).
"""

from __future__ import annotations

import time
from typing import Any

import aiohttp

from .const import APPLICATION_NAME


class BusyBarError(Exception):
    """Communication or API error."""


class BusyBarAuthError(BusyBarError):
    """Invalid or missing API key."""


class BusyBarApi:
    """Thin wrapper around the BUSY Bar HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        api_key: str | None = None,
    ) -> None:
        self._session = session
        self._base = f"http://{host}"
        self._api_key = api_key
        self._headers = {"X-API-Token": api_key} if api_key else {}

    @property
    def ws_url(self) -> str:
        """Status stream WebSocket URL (token goes in the query for WS)."""
        url = f"{self._base.replace('http://', 'ws://')}/api/status/ws"
        if self._api_key:
            url += f"?x-api-token={self._api_key}"
        return url

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                json=json,
                params=params,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (401, 403):
                    raise BusyBarAuthError(f"Auth failed for {path} ({resp.status})")
                if resp.status >= 400:
                    body = await resp.text()
                    raise BusyBarError(f"{method} {path} -> {resp.status}: {body[:200]}")
                if resp.content_type == "application/json":
                    return await resp.json()
                return {}
        except aiohttp.ClientError as err:
            raise BusyBarError(f"{method} {path} failed: {err}") from err

    # Device info

    async def version(self) -> dict[str, Any]:
        return await self._request("GET", "/api/version")

    async def status_device(self) -> dict[str, Any]:
        return await self._request("GET", "/api/status/device")

    async def name(self) -> dict[str, Any]:
        return await self._request("GET", "/api/name")

    # Busy status

    async def busy_snapshot(self) -> dict[str, Any]:
        return await self._request("GET", "/api/busy/snapshot")

    async def busy_snapshot_set(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "snapshot": snapshot,
            "snapshot_timestamp_ms": int(time.time() * 1000),
        }
        # Firmware uses PUT for snapshot updates (POST returns 405).
        return await self._request("PUT", "/api/busy/snapshot", json=payload)

    async def busy_profile(self, slot: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/busy/profiles/{slot}")

    async def busy_profile_set(self, slot: str, profile: dict[str, Any]) -> dict[str, Any]:
        profile = {**profile, "profile_timestamp_ms": int(time.time() * 1000)}
        return await self._request("PUT", f"/api/busy/profiles/{slot}", json=profile)

    async def busy_start(self, slot: str = "busy") -> None:
        """Start busy mode using the timer settings of the given profile slot."""
        profile = await self.busy_profile(slot)
        card_id = profile["id"]
        timer = profile.get("timer_settings", {"type": "INFINITE"})
        ttype = timer.get("type", "INFINITE")
        if ttype == "SIMPLE":
            snapshot: dict[str, Any] = {
                "type": "SIMPLE",
                "card_id": card_id,
                "time_left_ms": timer["total_time_ms"],
                "is_paused": False,
            }
        elif ttype == "INTERVAL":
            work_ms = timer["interval_work_ms"]
            # ponytail: assumes intervals start at work phase 0; adjust if
            # firmware rejects it once someone runs an interval profile.
            snapshot = {
                "type": "INTERVAL",
                "card_id": card_id,
                "current_interval": 0,
                "current_interval_time_total_ms": work_ms,
                "current_interval_time_left_ms": work_ms,
                "is_paused": False,
                "interval_settings": timer,
            }
        else:
            snapshot = {"type": "INFINITE", "card_id": card_id, "is_paused": False}
        await self.busy_snapshot_set(snapshot)

    async def busy_stop(self) -> None:
        await self.busy_snapshot_set({"type": "NOT_STARTED"})

    # Display

    async def display_draw(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/display/draw", json=payload)

    async def display_clear(self) -> dict[str, Any]:
        return await self._request("DELETE", "/api/display/draw")

    async def brightness(self) -> dict[str, Any]:
        return await self._request("GET", "/api/display/brightness")

    async def brightness_set(self, value: int | str) -> dict[str, Any]:
        # Firmware expects brightness as a query param, not a JSON body.
        return await self._request(
            "POST", "/api/display/brightness", params={"value": value}
        )

    # Audio

    async def audio_play(
        self, path: str | None = None, stock_path: str | None = None
    ) -> dict[str, Any]:
        # Firmware requires application_name in the body.
        body: dict[str, Any] = {"application_name": APPLICATION_NAME}
        if path:
            body["path"] = path
        else:
            body["stock_path"] = stock_path
        return await self._request("POST", "/api/audio/play", json=body)

    async def audio_stop(self) -> dict[str, Any]:
        return await self._request("DELETE", "/api/audio/play")

    async def volume(self) -> dict[str, Any]:
        return await self._request("GET", "/api/audio/volume")

    # Storage / themes / input

    async def storage_list(self, path: str) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/storage/list", params={"path": path})
        return data.get("list", [])

    async def themes(self) -> list[str]:
        entries = await self.storage_list("/ext/apps_assets/busy/themes")
        return sorted(e["name"] for e in entries if e.get("type") == "dir")

    async def press_key(self, key: str) -> dict[str, Any]:
        return await self._request("POST", "/api/input", params={"key": key})

    async def volume_set(self, volume: float) -> dict[str, Any]:
        # Firmware expects volume as an integer query param, like brightness.
        return await self._request(
            "POST", "/api/audio/volume", params={"volume": int(volume)}
        )
