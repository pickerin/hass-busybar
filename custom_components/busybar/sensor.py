"""Busy status sensor for BUSY Bar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BUSY_STATE_MAP
from .entity import BusyBarEntity
from .ws import signal_input


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    uid = entry.unique_id or entry.entry_id
    async_add_entities(
        [
            BusyStatusSensor(coordinator, uid),
            ModeSliderSensor(coordinator, uid, entry.entry_id),
        ]
    )


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


class ModeSliderSensor(BusyBarEntity, SensorEntity):
    """Position of the physical 5-way mode slider.

    Fed by the state stream; unknown until the slider first moves after
    HA starts (the Bar does not report the resting position).
    """

    _attr_translation_key = "mode_slider"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["busy", "custom", "off", "apps", "settings"]

    def __init__(self, coordinator, unique_id: str, entry_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._entry_id = entry_id
        self._attr_native_value = None
        self._attr_unique_id = f"{unique_id}_mode_slider"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_input(self._entry_id), self._handle_input
            )
        )

    @callback
    def _handle_input(self, update) -> None:
        if update["type"] == "switch":
            self._attr_native_value = update["position"]
            self.async_write_ha_state()
