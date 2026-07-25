"""Smoke test for BusyBarApi against a mock device.

Run from the repo root: python tests/smoke_test.py
Needs aiohttp (bundled with Home Assistant).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiohttp import ClientSession, web

from custom_components.busybar.api import BusyBarApi, BusyBarAuthError

calls = []


async def handler(request):
    body = await request.json() if request.can_read_body else None
    calls.append((request.method, request.path, dict(request.query), body))
    if request.path == "/api/version":
        if request.headers.get("X-API-Token") != "sekret":
            return web.Response(status=401)
        return web.json_response({"version": "1.0.2"})
    if request.path == "/api/busy/profiles/busy":
        return web.json_response(
            {
                "id": "card123",
                "title": "BUSY",
                "timer_settings": {"type": "SIMPLE", "total_time_ms": 1500000},
            }
        )
    return web.json_response({"success": True})


async def main():
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 18765)
    await site.start()

    async with ClientSession() as session:
        api = BusyBarApi(session, "127.0.0.1:18765", None)
        try:
            await api.version()
            raise AssertionError("expected auth error")
        except BusyBarAuthError:
            pass

        api = BusyBarApi(session, "127.0.0.1:18765", "sekret")
        assert (await api.version())["version"] == "1.0.2"

        await api.busy_start("busy")
        method, path, _, body = calls[-1]
        assert (method, path) == ("PUT", "/api/busy/snapshot")
        assert body["snapshot"] == {
            "type": "SIMPLE",
            "card_id": "card123",
            "time_left_ms": 1500000,
            "is_paused": False,
        }

        await api.busy_stop()
        assert calls[-1][3]["snapshot"] == {"type": "NOT_STARTED"}

        await api.brightness_set(55)
        assert calls[-1][2] == {"value": "55"}

        await api.display_draw(
            {
                "application_name": "homeassistant",
                "elements": [{"id": "ha_text", "type": "text", "text": "hi", "font": "normal"}],
            }
        )
        assert calls[-1][1] == "/api/display/draw"

        await api.audio_play(stock_path="alarm")
        assert calls[-1][3] == {"application_name": "homeassistant", "stock_path": "alarm"}

        await api.volume_set(40)
        assert calls[-1][2] == {"volume": "40"}

    await runner.cleanup()
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
