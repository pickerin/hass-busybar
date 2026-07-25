"""Busy screen (theme) selector for BUSY Bar."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BusyBarEntity


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([BusyScreenSelect(coordinator, entry.unique_id or entry.entry_id)])


class BusyScreenSelect(BusyBarEntity, SelectEntity):
    """Selects which screen (theme) the custom card displays."""

    _attr_translation_key = "busy_screen"

    def __init__(self, coordinator, unique_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._attr_unique_id = f"{unique_id}_busy_screen"

    @property
    def options(self) -> list[str]:
        return self.coordinator.data.get("themes", [])

    @property
    def current_option(self) -> str | None:
        profile = self.coordinator.data.get("profile_custom", {})
        return profile.get("busy_bar_settings", {}).get("theme")

    async def async_select_option(self, option: str) -> None:
        profile = dict(self.coordinator.data.get("profile_custom", {}))
        profile["busy_bar_settings"] = {
            **profile.get("busy_bar_settings", {}),
            "theme": option,
        }
        await self.coordinator.api.busy_profile_set("custom", profile)
        await self.coordinator.async_request_refresh()
