"""Busy mode switch for BUSY Bar."""

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
    async_add_entities([BusySwitch(coordinator, entry.unique_id or entry.entry_id)])


class BusySwitch(BusyBarEntity, SwitchEntity):
    """Start/stop busy mode using the BUSY profile's own timer settings."""

    _attr_translation_key = "busy"

    def __init__(self, coordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._attr_unique_id = f"{unique_id}_busy"

    @property
    def is_on(self) -> bool:
        snapshot = self.coordinator.data.get("snapshot", {})
        return snapshot.get("type", "NOT_STARTED") != "NOT_STARTED"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.busy_start("busy")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.busy_stop()
        await self.coordinator.async_request_refresh()
