"""The BUSY Bar integration."""

from __future__ import annotations

import voluptuous as vol

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client, config_validation as cv, device_registry as dr
from homeassistant.loader import async_get_integration

from .api import BusyBarApi, BusyBarAuthError, BusyBarError
from .const import (
    APPLICATION_NAME,
    CONF_API_KEY,
    DOMAIN,
    FONTS,
    INPUT_KEYS,
    SERVICE_CLEAR_DISPLAY,
    SERVICE_DRAW_TEXT,
    SERVICE_PLAY_AUDIO,
    SERVICE_PRESS_KEY,
    SERVICE_STOP_AUDIO,
)
from .coordinator import BusyBarCoordinator
from .views import BusyBarScreenView
from .ws import BusyBarWsListener

import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type BusyBarConfigEntry = ConfigEntry[BusyBarCoordinator]

DRAW_TEXT_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): cv.string,
        vol.Required("text"): cv.string,
        vol.Optional("display", default="front"): vol.In(["front", "back"]),
        vol.Optional("font", default="normal"): vol.In(FONTS),
        vol.Optional("color", default="#FFFFFF"): cv.string,
        vol.Optional("x", default=0): vol.Coerce(int),
        vol.Optional("y", default=0): vol.Coerce(int),
        vol.Optional("align"): vol.In(
            [
                "top_left",
                "top_mid",
                "top_right",
                "mid_left",
                "center",
                "mid_right",
                "bottom_left",
                "bottom_mid",
                "bottom_right",
            ]
        ),
        vol.Optional("timeout_ms"): vol.Coerce(int),
        vol.Optional("scroll_rate"): vol.Coerce(int),
    }
)

DEVICE_ONLY_SCHEMA = vol.Schema({vol.Optional("device_id"): cv.string})

PRESS_KEY_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): cv.string,
        vol.Required("key"): vol.In(INPUT_KEYS),
    }
)

PLAY_AUDIO_SCHEMA = vol.Schema(
    {
        vol.Optional("device_id"): cv.string,
        vol.Optional("path"): cv.string,
        vol.Optional("stock_path"): cv.string,
    }
)


def _api_for_call(hass: HomeAssistant, call: ServiceCall) -> BusyBarApi:
    """Resolve which BUSY Bar a service call targets."""
    entries: list[BusyBarConfigEntry] = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if getattr(e, "runtime_data", None)
    ]
    if not entries:
        raise BusyBarError("No BUSY Bar configured")
    device_id = call.data.get("device_id")
    if device_id:
        device = dr.async_get(hass).async_get(device_id)
        if device:
            for entry in entries:
                if entry.entry_id in device.config_entries:
                    return entry.runtime_data.api
        raise BusyBarError(f"No BUSY Bar found for device_id {device_id}")
    return entries[0].runtime_data.api


CARD_BASE_URL = "/busybar-static/busybar-card.js"


async def _async_register_card_resource(hass: HomeAssistant, card_url: str) -> None:
    """Add the card to Lovelace storage-mode resources (idempotent).

    add_extra_js_url alone is defeated by the frontend's service-worker
    cache on already-open browsers; a real Lovelace resource is loaded
    fresh on every dashboard render.
    """
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None)
    if resources is None or not hasattr(resources, "async_create_item"):
        return  # YAML resource mode; documented manual step
    try:
        await resources.async_get_info()  # ensures storage is loaded
        existing = [
            item
            for item in resources.async_items()
            if item.get("url", "").split("?")[0] == CARD_BASE_URL
        ]
        if not existing:
            await resources.async_create_item(
                {"res_type": "module", "url": card_url}
            )
        elif existing[0]["url"] != card_url:
            await resources.async_update_item(
                existing[0]["id"], {"url": card_url}
            )
    except Exception:  # noqa: BLE001 - resource registration is best-effort
        _LOGGER.exception("Could not register busybar-card Lovelace resource")


async def _async_setup_shared(hass: HomeAssistant) -> None:
    """One-time HTTP view, card asset, and resource registration."""
    if hass.data.get(f"{DOMAIN}_shared"):
        return
    hass.data[f"{DOMAIN}_shared"] = True
    hass.http.register_view(BusyBarScreenView(hass))
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/busybar-static",
                str(Path(__file__).parent / "www"),
                cache_headers=False,
            )
        ]
    )
    integration = await async_get_integration(hass, DOMAIN)
    card_url = f"{CARD_BASE_URL}?v={integration.version}"
    add_extra_js_url(hass, card_url)
    await _async_register_card_resource(hass, card_url)


async def async_setup_entry(hass: HomeAssistant, entry: BusyBarConfigEntry) -> bool:
    await _async_setup_shared(hass)
    session = aiohttp_client.async_get_clientsession(hass)
    api = BusyBarApi(session, entry.data[CONF_HOST], entry.data.get(CONF_API_KEY))

    try:
        await api.version()
    except BusyBarAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except BusyBarError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = BusyBarCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    device = dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, entry.unique_id or entry.entry_id)}
    )
    listener = BusyBarWsListener(
        hass, session, coordinator, entry.entry_id, device.id if device else None
    )
    coordinator.ws_listener = listener
    entry.async_create_background_task(
        hass, listener.run(), name=f"{DOMAIN}_state_stream"
    )

    async def handle_draw_text(call: ServiceCall) -> None:
        target = _api_for_call(hass, call)
        element = {
            "id": "ha_text",
            "type": "text",
            "text": call.data["text"],
            "font": call.data["font"],
            "color": call.data["color"],
            "x": call.data["x"],
            "y": call.data["y"],
            "display": call.data["display"],
        }
        if "align" in call.data:
            element["align"] = call.data["align"]
        if "timeout_ms" in call.data:
            element["timeout"] = call.data["timeout_ms"]
        if "scroll_rate" in call.data:
            element["scroll_rate"] = call.data["scroll_rate"]
        await target.display_draw(
            {"application_name": APPLICATION_NAME, "elements": [element]}
        )

    async def handle_clear_display(call: ServiceCall) -> None:
        await _api_for_call(hass, call).display_clear()

    async def handle_play_audio(call: ServiceCall) -> None:
        if bool(call.data.get("path")) == bool(call.data.get("stock_path")):
            raise BusyBarError("Provide exactly one of path or stock_path")
        await _api_for_call(hass, call).audio_play(
            path=call.data.get("path"), stock_path=call.data.get("stock_path")
        )

    async def handle_stop_audio(call: ServiceCall) -> None:
        await _api_for_call(hass, call).audio_stop()

    async def handle_press_key(call: ServiceCall) -> None:
        await _api_for_call(hass, call).press_key(call.data["key"])

    hass.services.async_register(
        DOMAIN, SERVICE_DRAW_TEXT, handle_draw_text, schema=DRAW_TEXT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_DISPLAY, handle_clear_display, schema=DEVICE_ONLY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_AUDIO, handle_play_audio, schema=PLAY_AUDIO_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_AUDIO, handle_stop_audio, schema=DEVICE_ONLY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PRESS_KEY, handle_press_key, schema=PRESS_KEY_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: BusyBarConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
