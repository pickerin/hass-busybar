"""Busy and custom-screen switches for BUSY Bar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    uid = entry.unique_id or entry.entry_id
    async_add_entities(
        [
            BusyCardSwitch(coordinator, uid, "busy", "busy"),
            BusyCardSwitch(coordinator, uid, "custom", "custom_screen"),
        ]
    )


class BusyCardSwitch(BusyBarEntity, SwitchEntity):
    """Starts/stops one of the Bar's two cards.

    The "busy" slot is the stock BUSY card; the "custom" slot shows the
    selected screen (theme). Each switch is on only while its own card
    is the one running.
    """

    def __init__(self, coordinator, unique_id: str, slot: str, key: str) -> None:
        super().__init__(coordinator, unique_id)
        self._slot = slot
        self._attr_translation_key = key
        self._attr_unique_id = f"{unique_id}_{key}" if key != "busy" else f"{unique_id}_busy"

    @property
    def is_on(self) -> bool:
        snapshot = self.coordinator.data.get("snapshot", {})
        if snapshot.get("type", "NOT_STARTED") == "NOT_STARTED":
            return False
        profile = self.coordinator.data.get(f"profile_{self._slot}", {})
        return snapshot.get("card_id") == profile.get("id")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.busy_start(self._slot)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.busy_stop()
        await self.coordinator.async_request_refresh()
