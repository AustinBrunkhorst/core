"""The snooz integration entities."""
from collections.abc import Callable

from pysnooz import SnoozCommandData, SnoozCommandResultStatus

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import Entity

from .models import SnoozConfigurationData


class SnoozEntity(Entity):
    """Base class for Snooz entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, data: SnoozConfigurationData) -> None:
        """Initialize the entity."""
        self._device = data.device
        self._attr_unique_id = data.device.address + self._attr_translation_key
        self._attr_device_info = data.device_info

    async def _async_execute_command(self, command: SnoozCommandData) -> None:
        result = await self._device.async_execute_command(command)

        if result.status == SnoozCommandResultStatus.SUCCESSFUL:
            self._async_write_state_changed()
        elif result.status != SnoozCommandResultStatus.CANCELLED:
            raise HomeAssistantError(
                f"Command {command} failed with status {result.status.name} after"
                f" {result.duration}"
            )

    @callback
    def _async_subscribe_to_device_change(self) -> Callable[[], None]:
        return self._device.subscribe_to_state_change(self._async_write_state_changed)
