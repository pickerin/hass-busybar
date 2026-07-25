"""Busy status sensor for BUSY Bar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUSY_STATE_MAP
from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([BusyStatusSensor(coordinator, entry.unique_id or entry.entry_id)])


class BusyStatusSensor(BusyBarEntity, SensorEntity):
    """Current busy mode state."""

    _attr_translation_key = "busy_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(BUSY_STATE_MAP.values())

    def __init__(self, coordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._attr_unique_id = f"{unique_id}_busy_status"

    @property
    def native_value(self) -> str | None:
        snapshot = self.coordinator.data.get("snapshot", {})
        return BUSY_STATE_MAP.get(snapshot.get("type"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self.coordinator.data.get("snapshot", {})
        attrs: dict[str, Any] = {}
        if "is_paused" in snapshot:
            attrs["paused"] = snapshot["is_paused"]
        if "time_left_ms" in snapshot:
            attrs["time_left_seconds"] = snapshot["time_left_ms"] // 1000
        if "card_id" in snapshot:
            attrs["card_id"] = snapshot["card_id"]
        if "current_interval" in snapshot:
            attrs["current_interval"] = snapshot["current_interval"]
            attrs["interval_time_left_seconds"] = (
                snapshot.get("current_interval_time_left_ms", 0) // 1000
            )
        return attrs
