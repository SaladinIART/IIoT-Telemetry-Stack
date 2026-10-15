from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

pytest.importorskip("asyncua")
from asyncua import ua

from iiot_stack.opcua_adapter import Freshness, ObservationRejected, map_snapshot
from iiot_stack.opcua_model import NODE_TYPES, loopback_endpoint


def snapshot():
    now = datetime.now(UTC) - timedelta(seconds=20)
    values = dict(zip(NODE_TYPES, [570.0, 550.0, 12, 2, 0, 1], strict=True))
    return {
        tag: ua.DataValue(ua.Variant(value, NODE_TYPES[tag]), SourceTimestamp=now)
        for tag, value in values.items()
    }


def test_good_steady_value_preserves_source_time_and_schema():
    data = snapshot()
    payloads = map_snapshot(data, seq=8, emitted_ms=2000000000000)
    assert len(payloads) == 5
    assert [p["seq"] for p in payloads] == list(range(8, 13))
    assert payloads[0]["source_ts"] == int(data["billet_temp_c"].SourceTimestamp.timestamp() * 1000)
    assert payloads[0]["source_ts"] != payloads[0]["ts"]
    assert payloads[0]["quality"] == "good"


@pytest.mark.parametrize(
    "code", [ua.StatusCodes.BadSensorFailure, ua.StatusCodes.UncertainSensorNotAccurate]
)
def test_non_good_is_rejected(code):
    data = snapshot()
    data["billet_temp_c"] = replace(data["billet_temp_c"], StatusCode_=ua.StatusCode(code))
    with pytest.raises(ObservationRejected, match="non_good_status"):
        map_snapshot(data)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_rejected(value):
    data = snapshot()
    data["billet_temp_c"] = replace(
        data["billet_temp_c"], Value=ua.Variant(value, ua.VariantType.Double)
    )
    with pytest.raises(ObservationRejected, match="invalid_number"):
        map_snapshot(data)


@pytest.mark.parametrize(
    "timestamp", [None, datetime(2026, 1, 1), datetime(1601, 1, 1, tzinfo=UTC)]
)
def test_invalid_timestamp_rejected(timestamp):
    data = snapshot()
    data["billet_temp_c"] = replace(data["billet_temp_c"], SourceTimestamp=timestamp)
    with pytest.raises(ObservationRejected):
        map_snapshot(data)


def test_wrong_type_unknown_state_and_missing_node_rejected():
    data = snapshot()
    data["billet_temp_c"] = replace(
        data["billet_temp_c"], Value=ua.Variant("570", ua.VariantType.String)
    )
    with pytest.raises(ObservationRejected, match="wrong_type"):
        map_snapshot(data)
    data = snapshot()
    data["state_code"] = replace(data["state_code"], Value=ua.Variant(99, ua.VariantType.UInt16))
    with pytest.raises(ObservationRejected, match="unknown_equipment_state"):
        map_snapshot(data)
    data = snapshot()
    del data["fault_code"]
    with pytest.raises(ObservationRejected):
        map_snapshot(data)


def test_equipment_fault_can_have_good_data():
    data = snapshot()
    data["state_code"] = replace(data["state_code"], Value=ua.Variant(3, ua.VariantType.UInt16))
    data["fault_code"] = replace(data["fault_code"], Value=ua.Variant(111, ua.VariantType.UInt16))
    assert all(
        p["state"] == "FAULTED" and p["quality"] == "good" and p["fault_code"] == 111
        for p in map_snapshot(data)
    )


def test_freshness_requires_progress_and_expires_on_sequence_not_value():
    tracker = Freshness(5)
    assert not tracker.observe(8, 100)
    assert not tracker.fresh(100)
    assert tracker.observe(9, 101)
    assert tracker.fresh(105)
    assert not tracker.observe(9, 105)
    assert not tracker.fresh(107)
    assert not tracker.observe(1, 108)
    assert not tracker.fresh(108)
    assert tracker.observe(2, 109)


@pytest.mark.parametrize(
    "endpoint",
    [
        "opc.tcp://0.0.0.0:4840/",
        "opc.tcp://192.168.1.2:4840/",
        "http://127.0.0.1:4840/",
        "opc.tcp://admin:password@localhost:4840/",
    ],
)
def test_unsecured_non_loopback_or_credentials_rejected(endpoint):
    with pytest.raises(ValueError):
        loopback_endpoint(endpoint)
