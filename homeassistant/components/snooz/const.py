"""Constants for the Snooz component."""

import logging

from pysnooz import SnoozDeviceModel

from homeassistant.const import Platform

DOMAIN = "snooz"
PLATFORMS: list[Platform] = [
    Platform.FAN,
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.SWITCH,
]

LOGGER = logging.getLogger(__package__)

SERVICE_TRANSITION_ON = "transition_on"
SERVICE_TRANSITION_OFF = "transition_off"

ATTR_VOLUME = "volume"
ATTR_DURATION = "duration"

DEFAULT_TRANSITION_DURATION = 20

CONF_FIRMWARE_VERSION = "firmware_version"

MODEL_NAMES = {
    SnoozDeviceModel.ORIGINAL: "SNOOZ Original",
    SnoozDeviceModel.PRO: "SNOOZ Pro",
    SnoozDeviceModel.BREEZ: "Breez",
}
