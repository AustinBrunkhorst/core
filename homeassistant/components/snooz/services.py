"""Sevices for the Snooz integration."""
from __future__ import annotations
from datetime import timedelta
import voluptuous as vol

from pysnooz import SnoozCommandData, SnoozDevice
from homeassistant.config_entries import ConfigEntry, ConfigEntryState

from homeassistant.const import ATTR_DEVICE_ID


from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, config_validation as cv

from .const import (
    ATTR_DURATION,
    ATTR_FAN_SPEED,
    ATTR_VOLUME,
    DEFAULT_TRANSITION_DURATION,
    DOMAIN,
    SERVICE_TRANSITION_OFF,
    SERVICE_TRANSITION_ON,
)


async def async_setup_services(hass: HomeAssistant) -> None:
    async def async_transition_on(call: ServiceCall):
        for device in await get_snooz_devices(hass, call.data[ATTR_DEVICE_ID]):
            volume = call.data.get(ATTR_VOLUME)
            fan_speed = call.data.get(ATTR_FAN_SPEED)

            def true_when_set(setting: float | None, default=True):
                if volume is None and fan_speed is None:
                    return default

                if setting is None:
                    return None

                return True

            await device.async_execute_command(
                SnoozCommandData(
                    on=true_when_set(volume),
                    volume=volume,
                    fan_on=true_when_set(volume),
                    fan_speed=fan_speed,
                    duration=timedelta(seconds=call.data[ATTR_DURATION]),
                )
            )

    async def async_transition_off(call: ServiceCall):
        for device in await get_snooz_devices(hass, call.data[ATTR_DEVICE_ID]):
            volume = call.data.get(ATTR_VOLUME, None)
            fan_speed = call.data.get(ATTR_FAN_SPEED, None)

            def false_when_set(on: bool | None, default=False):
                if volume is None and fan_speed is None:
                    return default

                if on is None:
                    return None

                return not on

            await device.async_execute_command(
                SnoozCommandData(
                    on=false_when_set(volume),
                    fan_on=false_when_set(fan_speed, False),
                    duration=timedelta(seconds=call.data[ATTR_DURATION]),
                )
            )

    transition_common = {
        vol.Required(ATTR_DEVICE_ID): cv.ensure_list,
        vol.Optional(ATTR_DURATION, default=DEFAULT_TRANSITION_DURATION): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=300)
        ),
    }

    percentage = vol.All(vol.Coerce(int), vol.Range(min=0, max=100))

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRANSITION_ON,
        async_transition_on,
        schema=vol.Schema(
            {
                **transition_common,
                vol.Optional(ATTR_VOLUME): percentage,
                vol.Optional(ATTR_FAN_SPEED): percentage,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TRANSITION_OFF,
        async_transition_off,
        schema=vol.Schema(
            vol.All(
                {
                    **transition_common,
                    vol.Optional(ATTR_VOLUME): vol.IsTrue(),
                    vol.Optional(ATTR_FAN_SPEED): vol.IsTrue(),
                }
            )
        ),
    )


async def get_snooz_devices(
    hass: HomeAssistant,
    device_ids: list[str],
) -> list[SnoozDevice]:
    config_entries = list[ConfigEntry]()
    registry = dr.async_get(hass)
    for target in device_ids:
        device = registry.async_get(target)
        if device:
            device_entries = list[ConfigEntry]()
            for entry_id in device.config_entries:
                entry = hass.config_entries.async_get_entry(entry_id)
                if entry and entry.domain == DOMAIN:
                    device_entries.append(entry)
            if not device_entries:
                raise HomeAssistantError(f"Device '{target}' is not a {DOMAIN} device")
            config_entries.extend(device_entries)
        else:
            raise HomeAssistantError(f"Device '{target}' not found in device registry")
    devices = list[SnoozDevice]()
    for config_entry in config_entries:
        if config_entry.state != ConfigEntryState.LOADED:
            raise HomeAssistantError(f"{config_entry.title} is not loaded")
        devices.append(hass.data[DOMAIN][config_entry.entry_id].device)
    return devices
