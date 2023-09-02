"""Climate representation of a Snooz device."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pysnooz import enable_auto_temp, set_temp_target, turn_fan_off

from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import SnoozEntity
from .models import SnoozConfigurationData


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Snooz climate entity from a config entry."""

    data: SnoozConfigurationData = hass.data[DOMAIN][entry.entry_id]

    if data.info.supports_fan:
        async_add_entities([SnoozAutoAirflowClimate(data)])


class SnoozAutoAirflowClimate(SnoozEntity, ClimateEntity, RestoreEntity):
    """Climate representation of a Breez device."""

    _attr_translation_key = "auto_airflow"
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]

    def __init__(self, data: SnoozConfigurationData) -> None:
        """Initialize a Breez climate entity."""
        SnoozEntity.__init__(self, data)
        self._hvac_mode = None
        self._hvac_action = None
        self._target_temperature = None
        self._current_temperature = None

    @callback
    def _async_write_state_changed(self) -> None:
        # cache state for restore entity
        if not self.assumed_state:
            self._hvac_mode = self._device_hvac_mode()
            self._hvac_action = self._device_hvac_action()
            self._target_temperature = self._device.state.target_temperature
            self._current_temperature = self._device.state.temperature

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to device events."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            self._attr_hvac_mode = last_state.attributes.get(ATTR_HVAC_MODE)
            self._attr_hvac_action = last_state.attributes.get(ATTR_HVAC_ACTION)
            self._attr_target_temperature = last_state.attributes.get(ATTR_TEMPERATURE)
            self._attr_current_temperature = last_state.attributes.get(
                ATTR_CURRENT_TEMPERATURE
            )

        self.async_on_remove(self._async_subscribe_to_device_change())

    @callback
    def _async_subscribe_to_device_change(self) -> Callable[[], None]:
        return self._device.subscribe_to_state_change(self._async_write_state_changed)

    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return not self._device.is_connected

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        return self._hvac_mode if self.assumed_state else self._device_hvac_mode()

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current HVAC action."""
        return self._hvac_mode if self.assumed_state else self._device_hvac_action()

    @property
    def target_temperature(self) -> int:
        """Return the current target temperature."""
        return (
            self._target_temperature
            if self.assumed_state
            else self._device.state.target_temperature
        )

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return (
            self._current_temperature
            if self.assumed_state
            else self._device.state.temperature
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        await self._async_execute_command(
            enable_auto_temp() if hvac_mode == HVACMode.FAN_ONLY else turn_fan_off()
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        await self._async_execute_command(
            set_temp_target(int(kwargs.get(ATTR_TEMPERATURE)))
        )

    def _device_hvac_mode(self) -> HVACMode:
        return (
            HVACMode.FAN_ONLY if self._device.state.fan_auto_enabled else HVACMode.OFF
        )

    def _device_hvac_action(self) -> HVACAction:
        return HVACAction.FAN if self._device.state.fan_on else HVACAction.OFF
