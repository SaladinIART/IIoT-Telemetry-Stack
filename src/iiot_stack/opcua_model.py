"""Small custom OPC UA model for the independent NEXUS furnace exercise."""

from __future__ import annotations

import math
from urllib.parse import urlparse

from asyncua import ua

from iiot_stack.contracts import load_register_map

NAMESPACE = "urn:salbotics:nexus:opcua:demo"
ENDPOINT = "opc.tcp://127.0.0.1:4840/nexus/"
ASSET = "furnace-01"
NODE_TYPES = {
    "billet_temp_c": ua.VariantType.Double,
    "preheat_zone_temp_c": ua.VariantType.Double,
    "billet_loaded_count": ua.VariantType.UInt32,
    "state_code": ua.VariantType.UInt16,
    "fault_code": ua.VariantType.UInt16,
    "acquisition_seq": ua.VariantType.UInt64,
}
BROWSE_NAMES = {
    "billet_temp_c": "BilletTemperature",
    "preheat_zone_temp_c": "PreheatZoneTemperature",
    "billet_loaded_count": "BilletLoadedCount",
    "state_code": "StateCode",
    "fault_code": "FaultCode",
    "acquisition_seq": "AcquisitionSequence",
}


def furnace_contract() -> dict:
    return next(a for a in load_register_map()["assets"] if a["asset_id"] == ASSET)


def loopback_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if (
        parsed.scheme != "opc.tcp"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is None
        or not 1 <= parsed.port <= 65535
    ):
        raise ValueError("This unsecured teaching endpoint must use loopback and an explicit port")
    return endpoint


def positive_seconds(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("seconds must be finite and positive")
    return result
