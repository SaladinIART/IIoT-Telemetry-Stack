from __future__ import annotations

import logging
import time

import paho.mqtt.client as mqtt
from pymodbus.client import ModbusTcpClient

from iiot_stack.industrial import fault_name, fault_severity, load_assets, state_name
from iiot_stack.logging_utils import configure_logging
from iiot_stack.settings import CollectorSettings
from iiot_stack.telemetry import (
    apply_scaling,
    build_event_payload,
    build_event_topic,
    build_payload,
    build_telemetry_topic,
    decode_words,
    payload_bytes,
)

LOG = logging.getLogger("collector")


def connect_mqtt(settings: CollectorSettings) -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{settings.mqtt_client_id_prefix}-collector-line",
        protocol=mqtt.MQTTv311,
    )
    client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()
    return client


def publish_status(
    client: mqtt.Client, settings: CollectorSettings, asset_id: str, quality: str, seq: int
) -> None:
    topic = build_event_topic(settings.site, settings.line, asset_id, "status")
    payload = build_event_payload(
        asset=asset_id,
        event_type="status",
        state="RUNNING" if quality == "good" else "FAULTED",
        fault_code=0 if quality == "good" else 999,
        severity="info" if quality == "good" else "warning",
        message=f"collector status is {quality}",
        seq=seq,
        reason_code="collector_status",
    )
    client.publish(topic, payload=payload_bytes(payload), qos=1, retain=True)


def run() -> None:
    configure_logging()
    settings = CollectorSettings()
    assets = load_assets()
    mqtt_client = connect_mqtt(settings)
    modbus_client = ModbusTcpClient(settings.modbus_host, port=settings.modbus_port, timeout=2.0)

    seq = 0
    asset_state_cache: dict[str, tuple[str, int]] = {}
    backoff_seconds = 1.0

    while True:
        try:
            if not modbus_client.connect():
                raise RuntimeError("modbus connect failed")

            for asset in assets:
                poll_interval_seconds = (
                    asset.get("poll_interval_ms", settings.default_poll_interval_ms) / 1000.0
                )
                signal_values: dict[str, float] = {}
                source_ts = int(time.time() * 1000)

                for signal in asset["signals"]:
                    result = modbus_client.read_holding_registers(
                        address=asset["base_address"] + signal["address_offset"],
                        count=signal["word_count"],
                        slave=asset["unit_id"],
                    )
                    if result.isError():
                        raise RuntimeError(
                            f"modbus read error for {asset['asset_id']} {signal['tag_id']}: {result}"
                        )

                    raw_value = decode_words(
                        result.registers, signal["datatype"], signal["endianness"]
                    )
                    signal_values[signal["tag_id"]] = apply_scaling(
                        raw_value, signal["scale"], signal["offset"]
                    )

                state_code = int(signal_values["state_code"])
                fault_code = int(signal_values["fault_code"])
                state = state_name(asset, state_code)
                fault_label = fault_name(asset, fault_code)
                quality = (
                    "bad" if state == "FAULTED" else "stale" if state == "MAINTENANCE" else "good"
                )
                last_state = asset_state_cache.get(asset["asset_id"])

                if last_state != (state, fault_code):
                    event_type = "alarm_raised" if fault_code != 0 else "state_changed"
                    if last_state is not None and last_state[1] != 0 and fault_code == 0:
                        event_type = "alarm_cleared"
                    if state == "MAINTENANCE":
                        event_type = "maintenance_started"
                    elif (
                        last_state is not None
                        and last_state[0] == "MAINTENANCE"
                        and state != "MAINTENANCE"
                    ):
                        event_type = "maintenance_ended"

                    event_payload = build_event_payload(
                        asset=asset["asset_id"],
                        event_type=event_type,
                        state=state,
                        fault_code=fault_code,
                        severity=fault_severity(state, fault_code),
                        message=f"{asset['name']} is {state.lower()} with {fault_label.lower()}",
                        seq=seq,
                        source_ts=source_ts,
                        reason_code=fault_label,
                    )
                    mqtt_client.publish(
                        build_event_topic(
                            settings.site, settings.line, asset["asset_id"], event_type
                        ),
                        payload=payload_bytes(event_payload),
                        qos=1,
                        retain=True,
                    )
                    seq += 1
                    asset_state_cache[asset["asset_id"]] = (state, fault_code)

                for signal in asset["signals"]:
                    tag_id = signal["tag_id"]
                    topic = build_telemetry_topic(
                        settings.site, settings.line, asset["asset_id"], tag_id
                    )
                    payload = build_payload(
                        asset=asset["asset_id"],
                        signal=tag_id,
                        value=signal_values[tag_id],
                        quality=quality,
                        seq=seq,
                        state=state,
                        fault_code=fault_code,
                        source_ts=source_ts,
                        reason_code=fault_label if fault_code != 0 else None,
                        unit=signal.get("unit"),
                        limits=signal.get("limits"),
                    )
                    mqtt_client.publish(topic, payload=payload_bytes(payload), qos=1, retain=False)
                    LOG.info(
                        "published telemetry",
                        extra={
                            "event": {
                                "asset": asset["asset_id"],
                                "signal": tag_id,
                                "seq": seq,
                                "value": signal_values[tag_id],
                                "state": state,
                                "fault_code": fault_code,
                                "quality": quality,
                            }
                        },
                    )
                    seq += 1

                publish_status(mqtt_client, settings, asset["asset_id"], quality, seq)
                seq += 1
                time.sleep(poll_interval_seconds)
            backoff_seconds = 1.0
        except Exception as exc:
            LOG.warning(
                "collector cycle failed",
                extra={"event": {"error": str(exc), "backoff_seconds": backoff_seconds}},
            )
            for asset in assets:
                publish_status(mqtt_client, settings, asset["asset_id"], "bad", seq)
                seq += 1
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 30.0)


if __name__ == "__main__":
    run()
