"""Light representation of a Snooz device."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pysnooz import turn_light_off, turn_light_on

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
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
    """Set up Snooz light entity from a config entry."""

    data: SnoozConfigurationData = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([SnoozLightEntity(data)])


class SnoozLightEntity(SnoozEntity, LightEntity, RestoreEntity):
    """Light representation of a Snooz device."""

    _attr_translation_key = "button_lights"
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, data: SnoozConfigurationData) -> None:
        """Initialize a Snooz light entity."""
        SnoozEntity.__init__(self, data)
        self._attr_unique_id = f"{self._device.address}-light"
        self._is_on: bool | None = None
        self._brightness: int | None = None

    @callback
    def _async_write_state_changed(self) -> None:
        # cache state for restore entity
        if not self.assumed_state:
            self._is_on = self._device.state.light_on
            self._brightness = _from_device_brightness(
                self._device.state.light_brightness
            )

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to device events."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            if last_state.state in (STATE_ON, STATE_OFF):
                self._is_on = last_state.state == STATE_ON
            else:
                self._is_on = None
            self._brightness = last_state.attributes.get(ATTR_BRIGHTNESS)

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
        """Return true if the light is on."""
        return self._is_on if self.assumed_state else self._device.state.light_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        return (
            self._brightness
            if self.assumed_state
            else _from_device_brightness(self._device.state.light_brightness)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn light on."""
        await self._async_execute_command(
            turn_light_on(brightness=_to_device_brightness(kwargs.get(ATTR_BRIGHTNESS)))
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn light off."""
        await self._async_execute_command(turn_light_off())


def _from_device_brightness(brightness: int | None) -> int | None:
    if brightness is None:
        return None

    return round(brightness * 2.55)


def _to_device_brightness(brightness: int | None) -> int | None:
    if brightness is None:
        return None

    return round(brightness / 2.55)
