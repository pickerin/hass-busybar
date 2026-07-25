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

SETTINGS = {"theme": "dnd", "show_work_phase_only": False, "trigger_smart_home": True}


async def handler(request):
    body = await request.json() if request.can_read_body else None
    calls.append((request.method, request.path, dict(request.query), body))
    if request.path == "/api/version":
        if request.headers.get("X-API-Token") != "sekret":
            return web.Response(status=401)
        return web.json_response({"version": "1.0.2"})
    if request.path == "/api/busy/profiles/busy" and request.method == "GET":
        return web.json_response(
            {
                "id": "card123",
                "title": "BUSY",
                "timer_settings": {"type": "SIMPLE", "total_time_ms": 1500000},
                "busy_bar_settings": SETTINGS,
            }
        )
    if request.path == "/api/busy/profiles/custom" and request.method == "GET":
        return web.json_response(
            {
                "id": "card456",
                "title": "custom",
                "timer_settings": {"type": "INFINITE"},
                "busy_bar_settings": SETTINGS,
            }
        )
    if request.path == "/api/storage/list":
        return web.json_response(
            {
                "list": [
                    {"type": "dir", "name": "on_air"},
                    {"type": "dir", "name": "meeting"},
                    {"type": "file", "name": "readme.txt", "size": 1},
                ]
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
            "busy_bar_settings": SETTINGS,
        }

        await api.busy_start("custom")
        assert calls[-1][3]["snapshot"] == {
            "type": "INFINITE",
            "card_id": "card456",
            "is_paused": False,
            "busy_bar_settings": SETTINGS,
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

        themes = await api.themes()
        assert themes == ["meeting", "on_air"], themes

        profile = await api.busy_profile("custom")
        profile["busy_bar_settings"] = {**profile["busy_bar_settings"], "theme": "on_air"}
        await api.busy_profile_set("custom", profile)
        method, path, _, body = calls[-1]
        assert (method, path) == ("PUT", "/api/busy/profiles/custom")
        assert body["busy_bar_settings"]["theme"] == "on_air"
        assert isinstance(body["profile_timestamp_ms"], int)

        await api.press_key("start")
        assert calls[-1][:3] == ("POST", "/api/input", {"key": "start"})

        assert api.ws_url == "ws://127.0.0.1:18765/api/status/ws?x-api-token=sekret"

    await runner.cleanup()
    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
