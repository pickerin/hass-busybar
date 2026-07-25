"""Brightness, volume, and busy timer controls for BUSY Bar."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import PERCENTAGE, UnitOfTime
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
            BrightnessNumber(coordinator, uid),
            VolumeNumber(coordinator, uid),
            BusyTimerNumber(coordinator, uid),
        ]
    )


class BrightnessNumber(BusyBarEntity, NumberEntity):
    """Display brightness (0-100; unknown while device is in auto mode)."""

    _attr_translation_key = "brightness"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._attr_unique_id = f"{unique_id}_brightness"

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get("brightness", {}).get("value")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None  # "auto" or missing

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.brightness_set(int(value))
        await self.coordinator.async_request_refresh()


class VolumeNumber(BusyBarEntity, NumberEntity):
    """Audio volume (0-100)."""

    _attr_translation_key = "volume"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._attr_unique_id = f"{unique_id}_volume"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("volume")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.volume_set(value)
        await self.coordinator.async_request_refresh()


class BusyTimerNumber(BusyBarEntity, NumberEntity):
    """Busy timer duration in minutes; 0 means untimed (infinite).

    Reflects the busy profile's timer settings. Setting a value rewrites
    them (SIMPLE countdown, or INFINITE at 0); interval/pomodoro profiles
    configured in the BUSY App show as 0 and are preserved until changed.
    """

    _attr_translation_key = "busy_timer"
    _attr_native_min_value = 0
    _attr_native_max_value = 480
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = "box"

    def __init__(self, coordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._attr_unique_id = f"{unique_id}_busy_timer"

    @property
    def native_value(self) -> float | None:
        timer = self.coordinator.data.get("profile", {}).get("timer_settings", {})
        if timer.get("type") == "SIMPLE":
            return timer.get("total_time_ms", 0) / 60000
        return 0

    async def async_set_native_value(self, value: float) -> None:
        profile = dict(self.coordinator.data.get("profile", {}))
        if value > 0:
            profile["timer_settings"] = {
                "type": "SIMPLE",
                "total_time_ms": int(value * 60000),
            }
        else:
            profile["timer_settings"] = {"type": "INFINITE"}
        await self.coordinator.api.busy_profile_set("busy", profile)
        await self.coordinator.async_request_refresh()
