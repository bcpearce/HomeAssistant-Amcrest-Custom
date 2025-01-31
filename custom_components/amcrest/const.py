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
