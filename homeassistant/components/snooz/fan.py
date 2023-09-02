"""Fan entities exposed for Snooz devices."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from pysnooz import (
    SnoozCommandData,
    set_fan_speed,
    set_volume,
    turn_fan_off,
    turn_fan_on,
    turn_off,
    turn_on,
)
import voluptuous as vol

from homeassistant.components.fan import ATTR_PERCENTAGE, FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_DURATION,
    ATTR_VOLUME,
    DEFAULT_TRANSITION_DURATION,
    DOMAIN,
    SERVICE_TRANSITION_OFF,
    SERVICE_TRANSITION_ON,
)
from .entity import SnoozEntity
from .models import SnoozConfigurationData


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Snooz/Breez fan entities from a config entry."""

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_TRANSITION_ON,
        {
            vol.Optional(ATTR_VOLUME): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            ),
            vol.Optional(ATTR_DURATION, default=DEFAULT_TRANSITION_DURATION): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
        },
        "async_transition_on",
    )
    platform.async_register_entity_service(
        SERVICE_TRANSITION_OFF,
        {
            vol.Optional(ATTR_DURATION, default=DEFAULT_TRANSITION_DURATION): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
        },
        "async_transition_off",
    )

    data: SnoozConfigurationData = hass.data[DOMAIN][entry.entry_id]

    entities = [SnoozWhiteNoiseFan(data)]

    if data.info.supports_fan:
        entities.append(SnoozAirflowFan(data))

    async_add_entities(entities)


class SnoozFan(SnoozEntity, FanEntity, RestoreEntity):
    """Base class for features exposed as fan entities on Snooz devices."""

    _attr_supported_features = FanEntityFeature.SET_SPEED

    def __init__(self, data: SnoozConfigurationData) -> None:
        """Initialize a Snooz fan entity."""
        SnoozEntity.__init__(self, data)
        self._is_on: bool | None = None
        self._percentage: int | None = None

    @callback
    def _async_write_state_changed(self) -> None:
        # cache state for restore entity
        if not self.assumed_state:
            self._is_on = self.feature_is_on
            self._percentage = self.feature_percentage

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to device events."""
        await super().async_added_to_hass()

        if last_state := await self.async_get_last_state():
            if last_state.state in (STATE_ON, STATE_OFF):
                self._is_on = last_state.state == STATE_ON
            else:
                self._is_on = None
            self._percentage = last_state.attributes.get(ATTR_PERCENTAGE)

        self.async_on_remove(self._async_subscribe_to_device_change())

    @property
    def percentage(self) -> int | None:
        """Volume level of the device."""
        return self._percentage if self.assumed_state else self.feature_percentage

    @property
    def is_on(self) -> bool | None:
        """Power state of the device."""
        return self._is_on if self.assumed_state else self.feature_is_on

    @property
    def assumed_state(self) -> bool:
        """Return True if unable to access real state of the entity."""
        return not self._device.is_connected

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the device."""
        await self._async_execute_command(self.turn_on_command(percentage))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the device."""
        await self._async_execute_command(self.turn_off_command())

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the volume of the device. A value of 0 will turn off the device."""
        await self._async_execute_command(
            self.set_percentage_command(percentage)
            if percentage > 0
            else self.turn_off_command()
        )

    async def async_transition_on(self, duration: int, **kwargs: Any) -> None:
        """Transition on the device."""
        await self._async_execute_command(
            self.turn_on_command(kwargs.get("volume"), timedelta(seconds=duration))
        )

    async def async_transition_off(self, duration: int, **kwargs: Any) -> None:
        """Transition off the device."""
        await self._async_execute_command(
            self.turn_off_command(duration=timedelta(seconds=duration))
        )

    @property
    def feature_is_on(self) -> bool:
        """Return True if the feature is currently on."""
        raise NotImplementedError()

    @property
    def feature_percentage(self) -> float:
        """Return the current feature percentage."""
        raise NotImplementedError()

    def turn_on_command(
        self, percentage: int | None = None, duration: timedelta | None = None
    ) -> SnoozCommandData:
        """Return the command to turn on the feature."""
        raise NotImplementedError()

    def turn_off_command(self, duration: timedelta | None = None) -> SnoozCommandData:
        """Return the command to turn off the feature."""
        raise NotImplementedError()

    def set_percentage_command(self, percentage: int) -> SnoozCommandData:
        """Return the command to set the feature percentage."""
        raise NotImplementedError()


class SnoozWhiteNoiseFan(SnoozFan):
    """Fan representation of the white noise feature on all Snooz devices."""

    _attr_translation_key = "white_noise"

    @property
    def feature_is_on(self) -> bool:
        return self._device.state.on

    @property
    def feature_percentage(self) -> bool:
        return self._device.state.on

    def turn_on_command(
        self, percentage: int | None = None, duration: timedelta | None = None
    ) -> SnoozCommandData:
        """Return the command to turn on the feature."""
        return turn_on(volume=percentage, duration=duration)

    def turn_off_command(self, duration: timedelta | None = None) -> SnoozCommandData:
        """Return the command to turn off the feature."""
        return turn_off(duration=duration)

    def set_percentage_command(self, percentage: int) -> SnoozCommandData:
        """Return the command to set the feature percentage."""
        return set_volume(percentage)


class SnoozAirflowFan(SnoozFan):
    """Fan representation of the airflow feature on Breez devices."""

    _attr_translation_key = "airflow"
    _attr_speed_count = 10

    @property
    def feature_is_on(self) -> bool:
        return self._device.state.fan_on

    @property
    def feature_percentage(self) -> bool:
        return self._device.state.fan_speed * 100

    def turn_on_command(
        self, percentage: int | None = None, duration: timedelta | None = None
    ) -> SnoozCommandData:
        """Return the command to turn on the feature."""
        return turn_fan_on(speed=percentage, duration=duration)

    def turn_off_command(self, duration: timedelta | None = None) -> SnoozCommandData:
        """Return the command to turn off the feature."""
        return turn_fan_off(duration=duration)

    def set_percentage_command(self, percentage: int) -> SnoozCommandData:
        """Return the command to set the feature percentage."""
        return set_fan_speed(percentage / 100)
