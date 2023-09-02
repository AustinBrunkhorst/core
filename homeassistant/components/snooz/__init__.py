"""The Snooz component."""
from __future__ import annotations

import logging

from pysnooz import SnoozDevice

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .models import SnoozConfigurationData


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Snooz device from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    token: str = entry.data[CONF_TOKEN]

    # transitions info logs are verbose. Only enable warnings
    logging.getLogger("transitions.core").setLevel(logging.WARNING)

    if not (ble_device := async_ble_device_from_address(hass, address)):
        raise ConfigEntryNotReady(
            f"Could not find Snooz with address {address}. Try power cycling the device"
        )

    device = SnoozDevice(ble_device, token)
    info = await device.async_get_info()

    if info is None:
        # make sure we don't hold onto the connection
        await device.async_disconnect()
        raise ConfigEntryError("Failed to get device information")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = SnoozConfigurationData(
        ble_device, device, info, entry.title
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    data: SnoozConfigurationData = hass.data[DOMAIN][entry.entry_id]
    if entry.title != data.title:
        await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data: SnoozConfigurationData = hass.data[DOMAIN][entry.entry_id]

        # also called by fan entities, but do it here too for good measure
        await data.device.async_disconnect()

        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.config_entries.async_entries(DOMAIN):
            hass.data.pop(DOMAIN)

    return unload_ok
