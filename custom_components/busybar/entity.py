"""Base entity for BUSY Bar."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BusyBarCoordinator


class BusyBarEntity(CoordinatorEntity[BusyBarCoordinator]):
    """Base entity tied to the coordinator and device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: BusyBarCoordinator, unique_id: str) -> None:
        super().__init__(coordinator)
        self._device_unique_id = unique_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name="BUSY Bar",
            manufacturer="Flipper Devices",
            model="BUSY Bar",
        )
