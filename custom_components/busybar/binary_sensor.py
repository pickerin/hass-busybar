"""Diagnostic connectivity sensor for the BUSY Bar state stream."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BusyBarEntity
from .ws import signal_connected


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    uid = entry.unique_id or entry.entry_id
    async_add_entities([StateStreamSensor(coordinator, uid, entry.entry_id)])


class StateStreamSensor(BusyBarEntity, BinarySensorEntity):
    """On while the WebSocket state stream is connected."""

    _attr_translation_key = "state_stream"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, unique_id: str, entry_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._entry_id = entry_id
        self._attr_is_on = False
        self._attr_unique_id = f"{unique_id}_state_stream"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        listener = getattr(self.coordinator, "ws_listener", None)
        if listener:
            self._attr_is_on = listener.connected
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, signal_connected(self._entry_id), self._handle_connected
            )
        )

    @callback
    def _handle_connected(self, connected: bool) -> None:
        self._attr_is_on = connected
        self.async_write_ha_state()
