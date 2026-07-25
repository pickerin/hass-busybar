"""Data update coordinator for BUSY Bar."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BusyBarApi, BusyBarAuthError, BusyBarError
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class BusyBarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls busy snapshot, brightness, and volume."""

    def __init__(self, hass: HomeAssistant, api: BusyBarApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            snapshot, brightness, volume = await asyncio.gather(
                self.api.busy_snapshot(),
                self.api.brightness(),
                self.api.volume(),
            )
        except BusyBarAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BusyBarError as err:
            raise UpdateFailed(str(err)) from err
        return {
            "snapshot": snapshot.get("snapshot", {}),
            "brightness": brightness,
            "volume": volume.get("volume"),
        }
