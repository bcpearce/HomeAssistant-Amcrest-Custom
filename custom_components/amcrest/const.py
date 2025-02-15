"""Constants for amcrest component."""

from enum import StrEnum
from typing import Final

DOMAIN: Final = "amcrest"
MANUFACTURER: Final = "Amcrest"

DEFAULT_PORT_HTTP = 80
CONF_MDNS: Final = "mdns"
CONF_STREAMS: Final = "streams"


class PtzAxes(StrEnum):
    """Possible  PTZ axes."""

    PAN = "pan"
    TILT = "tilt"
    ZOOM = "zoom"


class RotationOption(StrEnum):
    """Possible rotation options."""

    NONE = "none"
    CLOCKWISE_90 = "clockwise_90"
    FLIP_180 = "flip_180"
    CLOCKWISE_270 = "clockwise_270"
