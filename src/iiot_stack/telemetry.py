from __future__ import annotations

import json
import struct
import time
from typing import Any

from jsonschema import Draft202012Validator

from iiot_stack.contracts import load_event_schema, load_payload_schema

telemetry_validator = Draft202012Validator(load_payload_schema())
event_validator = Draft202012Validator(load_event_schema())


def build_telemetry_topic(site: str, line: str, asset: str, signal: str) -> str:
    return f"iiot/v1/telemetry/{site}/{line}/{asset}/{signal}"


def build_event_topic(site: str, line: str, asset: str, event_type: str) -> str:
    return f"iiot/v1/events/{site}/{line}/{asset}/{event_type}"


def parse_telemetry_topic(topic: str) -> tuple[str, str, str, str]:
    parts = topic.split("/")
    if len(parts) != 7 or parts[0] != "iiot" or parts[1] != "v1" or parts[2] != "telemetry":
        raise ValueError(f"invalid topic: {topic}")
    return parts[3], parts[4], parts[5], parts[6]


def parse_event_topic(topic: str) -> tuple[str, str, str, str]:
    parts = topic.split("/")
    if len(parts) != 7 or parts[0] != "iiot" or parts[1] != "v1" or parts[2] != "events":
        raise ValueError(f"invalid topic: {topic}")
    return parts[3], parts[4], parts[5], parts[6]


def decode_words(words: list[int], datatype: str, endianness: str) -> float:
    if datatype == "uint16":
        if len(words) != 1:
            raise ValueError("uint16 decoding requires one word")
        return float(words[0])
    if datatype == "uint32":
        if len(words) != 2:
            raise ValueError("uint32 decoding requires two words")
        if endianness != "big":
            raise ValueError("only big-endian uint32 is supported in this demo")
        return float((words[0] << 16) | words[1])
    if datatype == "float32":
        if len(words) != 2:
            raise ValueError("float32 decoding requires two words")
        if endianness != "big":
            raise ValueError("only big-endian float32 is supported in this demo")
        packed = struct.pack(">HH", words[0], words[1])
        return float(struct.unpack(">f", packed)[0])
    raise ValueError(f"unsupported datatype: {datatype}")


def apply_scaling(value: float, scale: float, offset: float) -> float:
    return value * scale + offset


def build_payload(
    asset: str,
    signal: str,
    value: float,
    quality: str,
    seq: int,
    state: str,
    fault_code: int,
    source_ts: int | None = None,
    reason_code: str | None = None,
    unit: str | None = None,
    limits: dict[str, float] | None = None,
    ts: int | None = None,
) -> dict[str, Any]:
    emitted_ts = int(ts if ts is not None else time.time() * 1000)
    payload: dict[str, Any] = {
        "v": 2,
        "ts": emitted_ts,
        "source_ts": int(source_ts if source_ts is not None else emitted_ts),
        "asset": asset,
        "signal": signal,
        "value": value,
        "quality": quality,
        "seq": seq,
        "state": state,
        "fault_code": int(fault_code),
    }
    if reason_code is not None:
        payload["reason_code"] = reason_code
    if unit is not None:
        payload["unit"] = unit
    if limits is not None:
        payload["limits"] = limits
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    telemetry_validator.validate(payload)


def build_event_payload(
    asset: str,
    event_type: str,
    state: str,
    fault_code: int,
    severity: str,
    message: str,
    seq: int,
    source_ts: int | None = None,
    reason_code: str | None = None,
    ts: int | None = None,
) -> dict[str, Any]:
    emitted_ts = int(ts if ts is not None else time.time() * 1000)
    payload: dict[str, Any] = {
        "v": 1,
        "ts": emitted_ts,
        "source_ts": int(source_ts if source_ts is not None else emitted_ts),
        "asset": asset,
        "event_type": event_type,
        "state": state,
        "fault_code": int(fault_code),
        "severity": severity,
        "message": message,
        "seq": seq,
    }
    if reason_code is not None:
        payload["reason_code"] = reason_code
    validate_event_payload(payload)
    return payload


def validate_event_payload(payload: dict[str, Any]) -> None:
    event_validator.validate(payload)


def payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")
