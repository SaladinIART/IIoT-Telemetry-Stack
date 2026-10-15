"""Actual loopback MQTT broker and OPC UA server, without Docker or hardware."""

from __future__ import annotations

import asyncio
import json
import socket
import threading

import pytest

pytest.importorskip("asyncua")
pytest.importorskip("amqtt")
import paho.mqtt.client as mqtt
from amqtt.broker import Broker

from iiot_stack.opcua_client import EvidenceLog, collect
from iiot_stack.opcua_mqtt import MqttSink
from iiot_stack.opcua_server import FurnaceServer
from iiot_stack.settings import CollectorSettings
from iiot_stack.telemetry import parse_telemetry_topic, validate_payload


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def broker(port):
    return Broker(
        {
            "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{port}"}},
            "plugins": {
                "amqtt.plugins.authentication.AnonymousAuthPlugin": {"allow_anonymous": True}
            },
        }
    )


@pytest.mark.asyncio
async def test_real_opcua_to_mqtt_and_broker_recovery(tmp_path):
    mqtt_port = free_port()
    endpoint = f"opc.tcp://127.0.0.1:{free_port()}/nexus/"
    server = broker(mqtt_port)
    await server.start()
    settings = CollectorSettings(mqtt_port=mqtt_port, mqtt_user="", mqtt_password="")
    sink = MqttSink(settings)
    received = []
    subscribed = threading.Event()
    subscriber = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id="nexus-opcua-test-observer"
    )
    subscriber.on_connect = lambda c, *_: c.subscribe("iiot/v1/telemetry/#", qos=1)
    subscriber.on_subscribe = lambda *_: subscribed.set()
    subscriber.on_message = lambda c, u, m: received.append((m.topic, json.loads(m.payload)))
    subscriber.connect_async("127.0.0.1", mqtt_port)
    subscriber.loop_start()
    log = EvidenceLog(tmp_path / "mqtt.jsonl")
    try:
        assert await asyncio.to_thread(subscribed.wait, 3)
        await sink.start()
        async with FurnaceServer(endpoint, interval=0.05):
            await collect(endpoint, duration=0.8, timeout=0.3, publish_ms=40, log=log, sink=sink)
        assert received
        for topic, payload in received:
            validate_payload(payload)
            assert parse_telemetry_topic(topic)[2:] == ("furnace-01", payload["signal"])
            assert payload["quality"] == "good"
        first_payload = received[0][1]
        await server.shutdown()
        for _ in range(30):
            if not sink.connected.is_set():
                break
            await asyncio.sleep(0.1)
        assert not await sink.publish(first_payload)
        log.write("mqtt_outage_observed", publication_succeeded=False)
        server = broker(mqtt_port)
        await server.start()
        for _ in range(80):
            if sink.connected.is_set():
                break
            await asyncio.sleep(0.1)
        assert sink.connected.is_set()
        assert await sink.publish({**first_payload, "seq": 100000})
        log.write("mqtt_recovery_observed", puback_received=True)
    finally:
        log.close()
        await sink.stop()
        subscriber.disconnect()
        await asyncio.to_thread(subscriber.loop_stop)
        await server.shutdown()
