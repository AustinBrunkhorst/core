"""Constants for the Snooz component."""

from pysnooz import SnoozDeviceModel

from homeassistant.const import Platform

DOMAIN = "snooz"
PLATFORMS: list[Platform] = [Platform.FAN, Platform.CLIMATE]

SERVICE_TRANSITION_ON = "transition_on"
SERVICE_TRANSITION_OFF = "transition_off"

ATTR_VOLUME = "volume"
ATTR_DURATION = "duration"
ATTR_FAN_SPEED = "fan_speed"

DEFAULT_TRANSITION_DURATION = 20

MODEL_NAMES = {
    SnoozDeviceModel.ORIGINAL: "SNOOZ Original",
    SnoozDeviceModel.PRO: "SNOOZ Pro",
    SnoozDeviceModel.BREEZ: "Breez",
}
