"""Constants for testing."""

from amcrest_api.config import Config as AmcrestFixedConfig
from amcrest_api.ptz import PtzCapabilityData, PtzPresetData

from custom_components.amcrest.data import AmcrestData

MOCK_FIXED_CONFIG = AmcrestFixedConfig(
    machine_name="AMC_TEST",
    network={},
    ptz_capabilities=PtzCapabilityData(preset=True),
    serial_number="123456",
    supported_events=[],
    software_version="1",
    session_physical_address="a0:60:32:ff:ff:ff",
    max_extra_stream=1,
)

MOCK_DATA_UPDATE = AmcrestData(
    ptz_presets=[PtzPresetData(1, "Preset1"), PtzPresetData(2, "Preset2")]
)
