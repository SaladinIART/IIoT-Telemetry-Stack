from __future__ import annotations

import pytest

from tools.verify_opcua_stack import matched_payload


def test_trace_survives_startup_gap_and_unflushed_latest_sample():
    first = {
        "asset": "furnace-01",
        "signal": "billet_temp_c",
        "seq": 0,
        "ts": 1000,
        "source_ts": 900,
        "value": 570.0,
    }
    stored = {**first, "seq": 5, "ts": 2000}
    latest = {**first, "seq": 10, "ts": 3000}
    records = []
    for payload in (first, stored, latest):
        records.extend(
            [
                {"kind": "telemetry", "payload": payload},
                {"kind": "mqtt_published", "seq": payload["seq"]},
            ]
        )
    # First was sent before ingestion subscribed; newest is not flushed yet.
    assert matched_payload(records, stored) == stored


def test_trace_rejects_missing_ack_and_wrong_timestamp():
    payload = {
        "asset": "furnace-01",
        "signal": "billet_temp_c",
        "seq": 5,
        "ts": 2000,
        "source_ts": 1900,
        "value": 570.0,
    }
    records = [{"kind": "telemetry", "payload": payload}]
    with pytest.raises(ValueError):
        matched_payload(records, payload)
    records.append({"kind": "mqtt_published", "seq": 5})
    with pytest.raises(ValueError):
        matched_payload(records, {**payload, "source_ts": 1901})
