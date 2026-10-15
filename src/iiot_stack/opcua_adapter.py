"""Conservative DataValue -> existing NEXUS v2 mapping and source freshness."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from asyncua import ua

from iiot_stack.opcua_model import ASSET, NODE_TYPES, furnace_contract
from iiot_stack.telemetry import build_payload


class ObservationRejected(ValueError):
    pass


def timestamp_ms(timestamp):
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise ObservationRejected("missing_or_naive_source_timestamp")
    result = int(timestamp.astimezone(UTC).timestamp() * 1000)
    if result < 0:
        raise ObservationRejected("invalid_source_timestamp")
    return result


def checked_value(tag, data):
    if data is None or data.StatusCode is None or not data.StatusCode.is_good():
        raise ObservationRejected(f"non_good_status:{tag}")
    if data.Value is None or data.Value.VariantType != NODE_TYPES[tag]:
        raise ObservationRejected(f"wrong_type:{tag}")
    value = data.Value.Value
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ObservationRejected(f"invalid_number:{tag}")
    if NODE_TYPES[tag] != ua.VariantType.Double:
        maximum = (1 << {"UInt16": 16, "UInt32": 32, "UInt64": 64}[NODE_TYPES[tag].name]) - 1
        if not isinstance(value, int) or not 0 <= value <= maximum:
            raise ObservationRejected(f"invalid_integer:{tag}")
    timestamp_ms(data.SourceTimestamp)
    return value


def map_snapshot(snapshot, *, seq=0, emitted_ms=None):
    contract = furnace_contract()
    values = {
        s["tag_id"]: checked_value(s["tag_id"], snapshot.get(s["tag_id"]))
        for s in contract["signals"]
    }
    state = contract["state_map"].get(str(values["state_code"]))
    if state is None:
        raise ObservationRejected("unknown_equipment_state")
    return [
        build_payload(
            asset=ASSET,
            signal=signal["tag_id"],
            value=values[signal["tag_id"]],
            quality="good",
            seq=seq + offset,
            state=state,
            fault_code=values["fault_code"],
            source_ts=timestamp_ms(snapshot[signal["tag_id"]].SourceTimestamp),
            ts=emitted_ms,
            unit=signal["unit"],
            limits=signal.get("limits"),
        )
        for offset, signal in enumerate(contract["signals"])
    ]


class Freshness:
    """Requires sequence progress after every new connection; never watches flat values."""

    def __init__(self, timeout=5.0):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self.timeout = timeout
        self.sequence = None
        self.progress_at = None

    def observe(self, sequence, now):
        if self.sequence is None:
            self.sequence = sequence
            return False
        if sequence < self.sequence:
            self.sequence, self.progress_at = sequence, None
            return False
        if sequence == self.sequence:
            return False
        self.sequence, self.progress_at = sequence, now
        return True

    def fresh(self, now):
        return self.progress_at is not None and now - self.progress_at <= self.timeout
