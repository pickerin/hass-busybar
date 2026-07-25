"""Screen (theme) and mode selectors for BUSY Bar."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
            BusyScreenSelect(coordinator, uid),
            ModeSelect(coordinator, uid, entry.entry_id),
        ]
    )


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
        # If the custom card is on screen, update the running snapshot too;
        # it renders from its own busy_bar_settings, not the stored profile.
        snap = (await self.coordinator.api.busy_snapshot()).get("snapshot", {})
        if (
            snap.get("type", "NOT_STARTED") != "NOT_STARTED"
            and snap.get("card_id") == profile.get("id")
        ):
            snap["busy_bar_settings"] = profile["busy_bar_settings"]
            await self.coordinator.api.busy_snapshot_set(snap)
        await self.coordinator.async_request_refresh()


class ModeSelect(BusyBarEntity, SelectEntity):
    """Commands the Bar's mode, mirroring the physical 5-way slider.

    Selecting injects the matching slider key; the firmware treats that
    exactly like a physical move and publishes the change back over the
    state stream, which keeps this entity in sync (including physical
    moves, which override any injected mode). Unknown until the first
    move after HA starts - the Bar only reports changes.
    """

    _attr_translation_key = "mode"
    _attr_options = ["busy", "custom", "off", "apps", "settings"]

    def __init__(self, coordinator, unique_id: str, entry_id: str) -> None:
        super().__init__(coordinator, unique_id)
        self._entry_id = entry_id
        self._attr_current_option = None
        self._attr_unique_id = f"{unique_id}_mode"

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
            self._attr_current_option = update["position"]
            self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.press_key(option)
        self._attr_current_option = option
        self.async_write_ha_state()
