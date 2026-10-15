from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import Mock

from iiot_stack.settings import IngestorSettings
from services.ingestor.app import Ingestor


def make_message(topic: str, payload: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(topic=topic, payload=json.dumps(payload).encode("utf-8"))


def test_ingestor_buffers_valid_messages() -> None:
    ingestor = Ingestor(IngestorSettings())
    ingestor.on_message(
        None,
        None,
        make_message(
            "iiot/v1/telemetry/site-a/line-1/asset-1/energy_kwh",
            {
                "v": 2,
                "ts": 1730000000000,
                "source_ts": 1730000000000,
                "asset": "asset-1",
                "signal": "energy_kwh",
                "value": 12.3,
                "quality": "good",
                "state": "RUNNING",
                "fault_code": 0,
                "seq": 9,
            },
        ),
    )
    assert len(ingestor.telemetry_buffer) == 1
    assert ingestor.telemetry_buffer[0]["signal"] == "energy_kwh"


def test_ingestor_drops_invalid_messages() -> None:
    ingestor = Ingestor(IngestorSettings())
    ingestor.on_message(
        None,
        None,
        make_message("iiot/v1/telemetry/site-a/line-1/asset-1/energy_kwh", {"bad": "payload"}),
    )
    assert ingestor.telemetry_buffer == []
    assert ingestor.event_buffer == []


def test_ingestor_buffers_event_messages() -> None:
    ingestor = Ingestor(IngestorSettings())
    ingestor.on_message(
        None,
        None,
        make_message(
            "iiot/v1/events/site-a/line-1/asset-1/alarm_raised",
            {
                "v": 1,
                "ts": 1730000000000,
                "source_ts": 1730000000000,
                "asset": "asset-1",
                "event_type": "alarm_raised",
                "state": "FAULTED",
                "fault_code": 301,
                "severity": "critical",
                "message": "Conveyor jam detected",
                "seq": 12,
            },
        ),
    )
    assert len(ingestor.event_buffer) == 1
    assert ingestor.event_buffer[0]["event_type"] == "alarm_raised"


def test_flush_if_due_writes_batch() -> None:
    ingestor = Ingestor(IngestorSettings(), max_batch=1)
    ingestor.telemetry_buffer.append(
        {
            "ts": 1730000000000,
            "source_ts": 1730000000000,
            "site": "site-a",
            "line": "line-1",
            "asset": "asset-1",
            "signal": "energy_kwh",
            "value": 12.3,
            "quality": "good",
            "state": "RUNNING",
            "fault_code": 0,
            "reason_code": None,
            "seq": 9,
        }
    )
    cur = Mock()
    ingestor.flush_if_due(cur)
    cur.executemany.assert_called_once()
    assert ingestor.telemetry_buffer == []


def test_flush_if_due_writes_event_batch() -> None:
    ingestor = Ingestor(IngestorSettings(), max_batch=1)
    ingestor.event_buffer.append(
        {
            "ts": 1730000000000,
            "source_ts": 1730000000000,
            "site": "site-a",
            "line": "line-1",
            "asset": "asset-1",
            "event_type": "alarm_raised",
            "state": "FAULTED",
            "fault_code": 301,
            "severity": "critical",
            "message": "Conveyor jam detected",
            "reason_code": "JAM_DETECTED",
            "seq": 12,
        }
    )
    cur = Mock()
    ingestor.flush_if_due(cur)
    cur.executemany.assert_called_once()
    assert ingestor.event_buffer == []
