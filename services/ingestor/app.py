from __future__ import annotations

import json
import logging
import time
from typing import Any

import paho.mqtt.client as mqtt
import psycopg

from iiot_stack.industrial import fault_severity
from iiot_stack.logging_utils import configure_logging
from iiot_stack.settings import IngestorSettings
from iiot_stack.telemetry import (
    parse_event_topic,
    parse_telemetry_topic,
    validate_event_payload,
    validate_payload,
)

LOG = logging.getLogger("ingestor")
TOPIC_FILTERS = [("iiot/v1/telemetry/+/+/+/+", 1), ("iiot/v1/events/+/+/+/+", 1)]
INSERT_TELEMETRY_SQL = """
INSERT INTO telemetry (ts, source_ts, site, line_name, asset, signal, value, quality, state, fault_code, reason_code, seq)
VALUES (
  to_timestamp(%(ts)s / 1000.0),
  to_timestamp(%(source_ts)s / 1000.0),
  %(site)s,
  %(line)s,
  %(asset)s,
  %(signal)s,
  %(value)s,
  %(quality)s,
  %(state)s,
  %(fault_code)s,
  %(reason_code)s,
  %(seq)s
)
ON CONFLICT DO NOTHING
"""
INSERT_EVENT_SQL = """
INSERT INTO events (ts, source_ts, site, line_name, asset, event_type, state, fault_code, severity, message, reason_code, seq)
VALUES (
  to_timestamp(%(ts)s / 1000.0),
  to_timestamp(%(source_ts)s / 1000.0),
  %(site)s,
  %(line)s,
  %(asset)s,
  %(event_type)s,
  %(state)s,
  %(fault_code)s,
  %(severity)s,
  %(message)s,
  %(reason_code)s,
  %(seq)s
)
ON CONFLICT DO NOTHING
"""


class Ingestor:
    def __init__(
        self, settings: IngestorSettings, max_batch: int = 200, max_delay_s: float = 1.0
    ) -> None:
        self.settings = settings
        self.max_batch = max_batch
        self.max_delay_s = max_delay_s
        self.telemetry_buffer: list[dict[str, Any]] = []
        self.event_buffer: list[dict[str, Any]] = []
        self.last_flush = time.time()

    def on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if msg.topic.startswith("iiot/v1/telemetry/"):
                validate_payload(payload)
                site, line, asset, signal = parse_telemetry_topic(msg.topic)
                self.telemetry_buffer.append(
                    {
                        "ts": int(payload["ts"]),
                        "source_ts": int(payload["source_ts"]),
                        "site": site,
                        "line": line,
                        "asset": asset,
                        "signal": signal,
                        "value": float(payload["value"]),
                        "quality": str(payload["quality"]),
                        "state": str(payload["state"]),
                        "fault_code": int(payload["fault_code"]),
                        "reason_code": payload.get("reason_code"),
                        "seq": int(payload["seq"]),
                    }
                )
            elif msg.topic.startswith("iiot/v1/events/"):
                validate_event_payload(payload)
                site, line, asset, event_type = parse_event_topic(msg.topic)
                self.event_buffer.append(
                    {
                        "ts": int(payload["ts"]),
                        "source_ts": int(payload["source_ts"]),
                        "site": site,
                        "line": line,
                        "asset": asset,
                        "event_type": event_type,
                        "state": str(payload["state"]),
                        "fault_code": int(payload["fault_code"]),
                        "severity": str(
                            payload.get(
                                "severity",
                                fault_severity(str(payload["state"]), int(payload["fault_code"])),
                            )
                        ),
                        "message": str(payload["message"]),
                        "reason_code": payload.get("reason_code"),
                        "seq": int(payload["seq"]),
                    }
                )
        except Exception as exc:
            LOG.warning(
                "dropping invalid message", extra={"event": {"topic": msg.topic, "error": str(exc)}}
            )

    def flush_if_due(self, cur: psycopg.Cursor[Any]) -> None:
        if not self.telemetry_buffer and not self.event_buffer:
            return
        now = time.time()
        total_rows = len(self.telemetry_buffer) + len(self.event_buffer)
        if total_rows < self.max_batch and (now - self.last_flush) < self.max_delay_s:
            return
        if self.telemetry_buffer:
            cur.executemany(INSERT_TELEMETRY_SQL, self.telemetry_buffer)
        if self.event_buffer:
            cur.executemany(INSERT_EVENT_SQL, self.event_buffer)
        LOG.info(
            "flushed ingestion batch",
            extra={
                "event": {
                    "telemetry_rows": len(self.telemetry_buffer),
                    "event_rows": len(self.event_buffer),
                }
            },
        )
        self.telemetry_buffer.clear()
        self.event_buffer.clear()
        self.last_flush = now


def connect_mqtt(ingestor: Ingestor) -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id="iiot-demo-ingestor", protocol=mqtt.MQTTv311
    )
    client.username_pw_set(ingestor.settings.mqtt_user, ingestor.settings.mqtt_password)
    client.on_message = ingestor.on_message
    client.connect(ingestor.settings.mqtt_host, ingestor.settings.mqtt_port, keepalive=30)
    client.subscribe(TOPIC_FILTERS)
    client.loop_start()
    return client


def run() -> None:
    configure_logging()
    settings = IngestorSettings()
    ingestor = Ingestor(settings=settings)

    while True:
        try:
            with psycopg.connect(settings.dsn) as conn:
                with conn.cursor() as cur:
                    mqtt_client = connect_mqtt(ingestor)
                    while True:
                        ingestor.flush_if_due(cur)
                        conn.commit()
                        time.sleep(0.2)
                    mqtt_client.loop_stop()
        except Exception as exc:
            LOG.warning("ingestor loop failed", extra={"event": {"error": str(exc)}})
            time.sleep(2.0)


if __name__ == "__main__":
    run()
