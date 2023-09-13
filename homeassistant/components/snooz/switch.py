"""Binary sensor representation of a Snooz device."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pysnooz import disable_night_mode, enable_night_mode

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import SnoozEntity
from .models import SnoozConfigurationData


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Snooz switch entity from a config entry."""

    data: SnoozConfigurationData = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([SnoozNightModeSwitchEntity(data)])


class SnoozNightModeSwitchEntity(SnoozEntity, SwitchEntity, RestoreEntity):
    """Switch entity representation of night mode for a Snooz device."""

    _attr_translation_key = "night_mode"

    def __init__(self, data: SnoozConfigurationData) -> None:
        """Initialize a Snooz night mode switch entity."""
        SnoozEntity.__init__(self, data)
        self._attr_unique_id = f"{self._device.address}-night-mode"
        self._is_on: bool | None = None

    @callback
    def _async_write_state_changed(self) -> None:
        # cache state for restore entity
        if not self.assumed_state:
            self._is_on = self._device.state.night_mode_enabled

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to device events."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            if last_state.state in (STATE_ON, STATE_OFF):
                self._is_on = last_state.state == STATE_ON
            else:
                self._is_on = None

        self.async_on_remove(self._async_subscribe_to_device_change())

    @callback
    def _async_subscribe_to_device_change(self) -> Callable[[], None]:
        return self._device.subscribe_to_state_change(self._async_write_state_changed)

    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return not self._device.is_connected

    @property
    def is_on(self) -> bool | None:
        """Return True if night mode is on."""
        return (
            self._is_on if self.assumed_state else self._device.state.night_mode_enabled
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn night mode on."""
        await self._async_execute_command(enable_night_mode())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn night mode off."""
        await self._async_execute_command(disable_night_mode())
