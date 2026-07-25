"""Event entities for the BUSY Bar's physical controls."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BusyBarEntity
from .ws import signal_input


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    uid = entry.unique_id or entry.entry_id
    async_add_entities(
        [
            ButtonEventEntity(coordinator, uid, entry.entry_id, "top_button", "start"),
            ButtonEventEntity(coordinator, uid, entry.entry_id, "ok_button", "ok"),
            ButtonEventEntity(coordinator, uid, entry.entry_id, "back_button", "back"),
            EncoderEventEntity(coordinator, uid, entry.entry_id),
        ]
    )


class BusyBarEventEntity(BusyBarEntity, EventEntity):
    """Base for input-driven event entities."""

    def __init__(self, coordinator, unique_id: str, entry_id: str, key: str) -> None:
        super().__init__(coordinator, unique_id)
        self._entry_id = entry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{unique_id}_{key}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_input(self._entry_id), self._handle_input
            )
        )

    @callback
    def _handle_input(self, update: dict[str, Any]) -> None:
        raise NotImplementedError


class ButtonEventEntity(BusyBarEventEntity):
    """Press/release events for one physical button."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["press", "release"]

    def __init__(
        self, coordinator, unique_id: str, entry_id: str, key: str, button: str
    ) -> None:
        super().__init__(coordinator, unique_id, entry_id, key)
        self._button = button

    @callback
    def _handle_input(self, update: dict[str, Any]) -> None:
        if update["type"] == "button" and update["button"] == self._button:
            self._trigger_event(update["action"])
            self.async_write_ha_state()


class EncoderEventEntity(BusyBarEventEntity):
    """Scroll wheel turn events with the rotation delta."""

    _attr_event_types = ["turn"]

    def __init__(self, coordinator, unique_id: str, entry_id: str) -> None:
        super().__init__(coordinator, unique_id, entry_id, "scroll_wheel")

    @callback
    def _handle_input(self, update: dict[str, Any]) -> None:
        if update["type"] == "encoder":
            self._trigger_event("turn", {"delta": update["delta"]})
            self.async_write_ha_state()
