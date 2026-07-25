"""Button entities that press the BUSY Bar's physical controls."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BusyBarEntity

BUTTONS = [
    ("press_top_button", "start"),
    ("press_ok", "ok"),
    ("press_back", "back"),
    ("scroll_up", "up"),
    ("scroll_down", "down"),
]


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    uid = entry.unique_id or entry.entry_id
    async_add_entities(
        BusyBarButton(coordinator, uid, key, input_key) for key, input_key in BUTTONS
    )


class BusyBarButton(BusyBarEntity, ButtonEntity):
    """Injects one physical control press."""

    def __init__(self, coordinator, unique_id: str, key: str, input_key: str) -> None:
        super().__init__(coordinator, unique_id)
        self._input_key = input_key
        self._attr_translation_key = key
        self._attr_unique_id = f"{unique_id}_{key}"

    async def async_press(self) -> None:
        await self.coordinator.api.press_key(self._input_key)
