"""Bounded optional MQTT sink; source quality never comes from broker state."""

from __future__ import annotations

import asyncio
import threading

import paho.mqtt.client as mqtt

from iiot_stack.telemetry import build_telemetry_topic, payload_bytes


class MqttSink:
    def __init__(self, settings):
        self.settings = settings
        self.connected = threading.Event()
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"{settings.mqtt_client_id_prefix}-opcua",
            protocol=mqtt.MQTTv311,
        )
        self.client.max_queued_messages_set(1)
        self.client.max_inflight_messages_set(1)
        self.client.reconnect_delay_set(1, 5)
        if settings.mqtt_user:
            self.client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            self.connected.set()

    def _on_disconnect(self, *args):
        self.connected.clear()

    async def start(self):
        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=10)
        self.client.loop_start()
        await asyncio.to_thread(self.connected.wait, 2)

    async def publish(self, payload):
        if not self.connected.is_set():
            return False
        topic = build_telemetry_topic(
            self.settings.site, self.settings.line, payload["asset"], payload["signal"]
        )
        info = self.client.publish(topic, payload_bytes(payload), qos=1, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            return False
        try:
            await asyncio.to_thread(info.wait_for_publish, 1)
            return info.is_published()
        except (RuntimeError, ValueError):
            return False

    async def stop(self):
        self.client.disconnect()
        await asyncio.to_thread(self.client.loop_stop)
