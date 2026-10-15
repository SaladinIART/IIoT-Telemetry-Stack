"""Browse, read and subscribe; retain evidence and optionally bridge to NEXUS MQTT."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from asyncua import Client, ua

from iiot_stack.opcua_adapter import Freshness, ObservationRejected, checked_value, map_snapshot
from iiot_stack.opcua_model import (
    ASSET,
    ENDPOINT,
    NAMESPACE,
    NODE_TYPES,
    furnace_contract,
    loopback_endpoint,
    positive_seconds,
)


class EvidenceLog:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.handle = None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.handle = self.path.open("x", encoding="utf-8")

    def write(self, kind, **fields):
        record = {"kind": kind, "received_at": datetime.now(UTC).isoformat(), **fields}
        if self.handle:
            self.handle.write(json.dumps(record, allow_nan=False) + "\n")
            self.handle.flush()

    def close(self):
        if self.handle:
            self.handle.close()


def observation(data):
    value = data.Value.Value if data.Value else None
    if isinstance(value, float) and not math.isfinite(value):
        value = str(value)
    return {
        "value": value,
        "variant_type": data.Value.VariantType.name if data.Value else None,
        "status_code": data.StatusCode.value if data.StatusCode else None,
        "status_name": data.StatusCode.name if data.StatusCode else None,
        "source_timestamp": data.SourceTimestamp.isoformat() if data.SourceTimestamp else None,
        "server_timestamp": data.ServerTimestamp.isoformat() if data.ServerTimestamp else None,
    }


class Handler:
    def __init__(self, queue, node_tags, log):
        self.queue, self.node_tags, self.log = queue, node_tags, log
        self.overflow = False

    def datachange_notification(self, node, value, data):
        tag = self.node_tags[node.nodeid.to_string()]
        if self.queue.full():
            self.overflow = True
            self.log.write("queue_overflow", action="disconnect_and_resubscribe")
            return
        self.queue.put_nowait((tag, data.monitored_item.Value, time.monotonic()))


async def collect(
    endpoint=ENDPOINT,
    *,
    duration=None,
    timeout=5.0,
    publish_ms=500.0,
    log=None,
    sink=None,
    retry_delay=1.0,
):
    loopback_endpoint(endpoint)
    positive_seconds(str(timeout))
    positive_seconds(str(publish_ms))
    positive_seconds(str(retry_delay))
    if duration is not None:
        positive_seconds(str(duration))
    log = log or EvidenceLog()
    deadline = time.monotonic() + duration if duration is not None else math.inf
    sequence = 0
    connection = 0
    log.write("run_started", endpoint=endpoint, simulated_equipment=True, timeout_seconds=timeout)
    while time.monotonic() < deadline:
        try:
            async with Client(endpoint, timeout=2, watchdog_intervall=0.5) as client:
                connection += 1
                freshness = Freshness(timeout)
                ns = await client.get_namespace_index(NAMESPACE)
                asset = await client.nodes.objects.get_child([f"{ns}:NEXUS", f"{ns}:Furnace01"])
                browsed = {child.nodeid.to_string() for child in await asset.get_children()}
                nodes = {
                    tag: client.get_node(ua.NodeId(f"{ASSET}.{tag}", ns)) for tag in NODE_TYPES
                }
                expected_units = {s["tag_id"]: s["unit"] for s in furnace_contract()["signals"]}
                for tag, node in nodes.items():
                    if node.nodeid.to_string() not in browsed:
                        raise ObservationRejected(f"missing_node:{tag}")
                    actual_type = await node.read_data_type_as_variant_type()
                    access = await node.get_user_access_level()
                    if actual_type != NODE_TYPES[tag] or ua.AccessLevel.CurrentWrite in access:
                        raise ObservationRejected(f"incompatible_node:{tag}")
                    unit = await node.get_child(f"{ns}:Unit")
                    unit_value = await unit.read_value()
                    if unit_value != expected_units.get(tag, "count"):
                        raise ObservationRejected(f"incompatible_unit:{tag}")
                    log.write(
                        "browse",
                        tag=tag,
                        node_id=node.nodeid.to_string(),
                        datatype=actual_type.name,
                        unit=unit_value,
                        access=[a.name for a in access],
                    )
                snapshot = dict(
                    zip(nodes, await client.read_attributes(nodes.values()), strict=True)
                )
                freshness.observe(
                    checked_value("acquisition_seq", snapshot["acquisition_seq"]), time.monotonic()
                )
                for tag, data in snapshot.items():
                    log.write("initial_read", tag=tag, **observation(data))
                queue = asyncio.Queue(maxsize=256)
                handler = Handler(queue, {n.nodeid.to_string(): t for t, n in nodes.items()}, log)
                subscription = await client.create_subscription(publish_ms, handler)
                try:
                    handles = await subscription.subscribe_data_change(
                        list(nodes.values()), queuesize=8
                    )
                    for handle in handles:
                        if isinstance(handle, ua.StatusCode):
                            handle.check()
                    revised = subscription.parameters
                    log.write(
                        "connected",
                        connection=connection,
                        namespace_index=ns,
                        requested_publish_ms=publish_ms,
                        revised_publish_ms=revised.RequestedPublishingInterval,
                        coherent_snapshot=False,
                    )
                    stale_reported = False
                    session_started = time.monotonic()
                    while time.monotonic() < deadline:
                        await client.check_connection()
                        if handler.overflow:
                            raise ObservationRejected("notification_queue_overflow")
                        if time.monotonic() - session_started > timeout and not freshness.fresh(
                            time.monotonic()
                        ):
                            if not stale_reported:
                                log.write("acquisition_stale", connection=connection)
                                stale_reported = True
                        try:
                            tag, data, received_mono = await asyncio.wait_for(
                                queue.get(),
                                timeout=min(0.1, max(0.001, deadline - time.monotonic())),
                            )
                        except TimeoutError:
                            continue
                        snapshot[tag] = data
                        log.write(
                            "observation", connection=connection, tag=tag, **observation(data)
                        )
                        if tag != "acquisition_seq":
                            continue
                        try:
                            acquired = checked_value(tag, data)
                            progressed = freshness.observe(acquired, received_mono)
                            if not progressed or not freshness.fresh(time.monotonic()):
                                continue
                            if stale_reported:
                                log.write("acquisition_recovered", connection=connection)
                                stale_reported = False
                            payloads = map_snapshot(snapshot, seq=sequence)
                        except ObservationRejected as exc:
                            log.write("rejected", reason=str(exc), connection=connection)
                            continue
                        for payload in payloads:
                            if not freshness.fresh(time.monotonic()):
                                log.write(
                                    "processing_delayed", action="suppress_remaining_snapshot"
                                )
                                break
                            sequence += 1
                            log.write("telemetry", connection=connection, payload=payload)
                            if sink is not None:
                                published = await sink.publish(payload)
                                log.write(
                                    "mqtt_published" if published else "mqtt_unavailable",
                                    seq=payload["seq"],
                                )
                finally:
                    try:
                        await subscription.delete()
                    except Exception as exc:
                        log.write("subscription_cleanup_failed", error_type=type(exc).__name__)
        except (OSError, TimeoutError, ua.UaError, ConnectionError, ObservationRejected) as exc:
            log.write(
                "transport_unavailable",
                error_type=type(exc).__name__,
                detail=str(exc),
                connection=connection,
            )
            await asyncio.sleep(min(retry_delay, max(0, deadline - time.monotonic())))
    log.write("run_finished", connections=connection, telemetry_candidates=sequence)
    return sequence


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--endpoint", default=ENDPOINT, type=loopback_endpoint)
    result.add_argument("--duration", type=positive_seconds)
    result.add_argument("--timeout", default=5.0, type=positive_seconds)
    result.add_argument("--publish-ms", default=500.0, type=positive_seconds)
    result.add_argument(
        "--output",
        default=f"{os.getenv('OPCUA_EVIDENCE_DIR', 'tmp')}/opcua-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.jsonl",
    )
    result.add_argument(
        "--mqtt", action="store_true", help="Bridge approved samples to configured MQTT broker"
    )
    return result


async def run_args(args):
    sink = None
    log = EvidenceLog(args.output)
    try:
        if args.mqtt:
            from iiot_stack.opcua_mqtt import MqttSink
            from iiot_stack.settings import CollectorSettings

            sink = MqttSink(CollectorSettings())
            await sink.start()
        return await collect(
            args.endpoint,
            duration=args.duration,
            timeout=args.timeout,
            publish_ms=args.publish_ms,
            log=log,
            sink=sink,
        )
    finally:
        if sink:
            await sink.stop()
        log.close()


def main():
    args = parser().parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(run_args(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
