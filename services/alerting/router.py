from __future__ import annotations

import json
import logging
import queue
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import paho.mqtt.client as mqtt
import psycopg

from iiot_stack.logging_utils import configure_logging
from iiot_stack.settings import AlertingSettings

from .detector import AlertDetector
from .rules import AlertRule, RuleLoader

LOG = logging.getLogger("alerting.router")

_INSERT_ALERT_SQL = """
INSERT INTO alerts (site, line_name, asset, signal, alert_type, severity, value, threshold, message, rule_id)
VALUES (%(site)s, %(line_name)s, %(asset)s, %(signal)s, %(alert_type)s, %(severity)s,
        %(value)s, %(threshold)s, %(message)s, %(rule_id)s::uuid)
RETURNING id::text, opened_at
"""

_FETCH_OPEN_THRESHOLD_SQL = """
SELECT id::text, asset, signal
FROM alerts
WHERE state IN ('OPEN', 'ACKED') AND alert_type = 'threshold'
"""

_LATEST_VALUE_SQL = """
SELECT value FROM telemetry
WHERE asset = %s AND signal = %s
ORDER BY ts DESC LIMIT 1
"""

_CLOSE_ALERT_SQL = """
UPDATE alerts SET state = 'CLOSED', closed_at = now() WHERE id = %s::uuid
"""

_CLOSE_OLD_TRANSIENT_SQL = """
UPDATE alerts SET state = 'CLOSED', closed_at = now()
WHERE state IN ('OPEN', 'ACKED')
  AND alert_type IN ('statistical', 'ml')
  AND opened_at < now() - INTERVAL '10 minutes'
"""


class AlertRouter:
    """
    Processes alert dicts from the queue: deduplication, DB persistence,
    MQTT publish, optional webhook routing, and periodic auto-close.

    Deduplication: the same (asset, signal, alert_type) combination is
    suppressed within dedup_window_sec to prevent alert fatigue during
    sustained fault conditions (the first alert is the actionable one).

    Auto-close runs every 60 seconds:
    - Threshold alerts: closed when the latest telemetry value is back in bounds.
    - Statistical/ML alerts: closed after 10 minutes (transient by nature).
    """

    def __init__(
        self,
        dsn: str,
        mqtt_client: mqtt.Client,
        rule_loader: RuleLoader,
        alert_queue: queue.Queue[dict[str, Any]],
        dedup_window_sec: float = 300.0,
        webhook_url: str = "",
    ) -> None:
        self._dsn = dsn
        self._mqtt = mqtt_client
        self._rules = rule_loader
        self._queue = alert_queue
        self._dedup_window_sec = dedup_window_sec
        self._webhook_url = webhook_url
        # (asset, signal, alert_type) → timestamp of last successful insert
        self._dedup: dict[tuple[str, str, str], float] = {}
        self._last_auto_close: float = 0.0

    def drain(self, conn: psycopg.Connection[Any]) -> None:
        """Drain all pending alerts from the queue. Call in the main loop."""
        with conn.cursor() as cur:
            while True:
                try:
                    alert = self._queue.get_nowait()
                except queue.Empty:
                    break
                self._process(alert, cur)
        conn.commit()

    def auto_close(self, conn: psycopg.Connection[Any]) -> None:
        """Periodically close resolved alerts. Call in the main loop."""
        if time.time() - self._last_auto_close < 60.0:
            return
        self._last_auto_close = time.time()
        closed = 0
        try:
            with conn.cursor() as cur:
                # Close old statistical/ml alerts unconditionally
                cur.execute(_CLOSE_OLD_TRANSIENT_SQL)
                closed += cur.rowcount

                # Close threshold alerts whose value has returned to bounds
                cur.execute(_FETCH_OPEN_THRESHOLD_SQL)
                open_alerts = cur.fetchall()
                for alert_id, asset, signal in open_alerts:
                    cur.execute(_LATEST_VALUE_SQL, (asset, signal))
                    row = cur.fetchone()
                    if row is None:
                        continue
                    rule = self._rules.get(asset, signal)
                    if rule is None:
                        continue
                    if _value_in_bounds(float(row[0]), rule):
                        cur.execute(_CLOSE_ALERT_SQL, (alert_id,))
                        closed += 1
                        # Clear dedup so the alert can re-fire if the condition returns
                        for atype in ("threshold", "statistical", "ml"):
                            self._dedup.pop((asset, signal, atype), None)

            conn.commit()
            if closed:
                LOG.info("auto-closed alerts", extra={"event": {"count": closed}})
        except Exception as exc:
            LOG.warning("auto-close failed", extra={"event": {"error": str(exc)}})

    # ── private ──────────────────────────────────────────────────────────────

    def _process(self, alert: dict[str, Any], cur: psycopg.Cursor[Any]) -> None:
        key = (alert["asset"], alert["signal"], alert["alert_type"])
        now = time.time()
        if now - self._dedup.get(key, 0.0) < self._dedup_window_sec:
            LOG.debug(
                "alert deduped",
                extra={
                    "event": {
                        "asset": alert["asset"],
                        "signal": alert["signal"],
                        "type": alert["alert_type"],
                    }
                },
            )
            return

        self._dedup[key] = now
        try:
            cur.execute(
                _INSERT_ALERT_SQL,
                {
                    "site": alert["site"],
                    "line_name": alert["line_name"],
                    "asset": alert["asset"],
                    "signal": alert["signal"],
                    "alert_type": alert["alert_type"],
                    "severity": alert["severity"],
                    "value": alert["value"],
                    "threshold": alert.get("threshold"),
                    "message": alert["message"],
                    "rule_id": alert.get("rule_id"),
                },
            )
            row = cur.fetchone()
            if row is None:
                return
            alert_id, opened_at = row[0], row[1]
        except Exception as exc:
            LOG.warning("alert insert failed", extra={"event": {"error": str(exc)}})
            return

        LOG.info(
            "alert inserted",
            extra={
                "event": {
                    "id": alert_id,
                    "asset": alert["asset"],
                    "signal": alert["signal"],
                    "type": alert["alert_type"],
                    "severity": alert["severity"],
                    "value": alert["value"],
                }
            },
        )
        self._publish_mqtt(alert, alert_id, opened_at)
        if self._webhook_url:
            self._post_webhook(alert, alert_id)

    def _publish_mqtt(self, alert: dict[str, Any], alert_id: str, opened_at: Any) -> None:
        topic = f"iiot/v1/alerts/{alert['site']}/{alert['line_name']}/{alert['asset']}/{alert_id}"
        ts_ms = int(time.time() * 1000)
        opened_ts_ms = (
            int(opened_at.timestamp() * 1000) if hasattr(opened_at, "timestamp") else ts_ms
        )
        payload = {
            "v": 1,
            "id": alert_id,
            "ts": ts_ms,
            "site": alert["site"],
            "line_name": alert["line_name"],
            "asset": alert["asset"],
            "signal": alert["signal"],
            "alert_type": alert["alert_type"],
            "severity": alert["severity"],
            "value": alert["value"],
            "threshold": alert.get("threshold"),
            "state": "OPEN",
            "message": alert["message"],
            "opened_at": opened_ts_ms,
            "acked_at": None,
            "closed_at": None,
            "rule_id": alert.get("rule_id"),
        }
        try:
            self._mqtt.publish(
                topic,
                payload=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                qos=1,
                retain=False,
            )
        except Exception as exc:
            LOG.warning("mqtt publish failed", extra={"event": {"error": str(exc)}})

    def _post_webhook(self, alert: dict[str, Any], alert_id: str) -> None:
        body = json.dumps(
            {
                "text": (
                    f"[{alert['severity'].upper()}] {alert['asset']} — {alert['signal']}: "
                    f"{alert['message']} (id={alert_id[:8]})"
                )
            }
        ).encode("utf-8")
        req = Request(
            self._webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=5) as resp:
                LOG.info("webhook sent", extra={"event": {"status": resp.status}})
        except URLError as exc:
            LOG.warning("webhook failed", extra={"event": {"error": str(exc)}})


def _value_in_bounds(value: float, rule: AlertRule) -> bool:
    """Return True if value does not violate any threshold in the rule."""
    if rule.crit_low is not None and value < rule.crit_low:
        return False
    if rule.crit_high is not None and value > rule.crit_high:
        return False
    if rule.warn_low is not None and value < rule.warn_low:
        return False
    if rule.warn_high is not None and value > rule.warn_high:
        return False
    return True


def _connect_mqtt(settings: AlertingSettings) -> mqtt.Client:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"{settings.mqtt_client_id_prefix}-alerting",
        protocol=mqtt.MQTTv311,
    )
    client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    client.loop_start()
    return client


def run() -> None:
    configure_logging()
    settings = AlertingSettings()
    alert_queue: queue.Queue[dict[str, Any]] = queue.Queue()
    rule_loader = RuleLoader(dsn=settings.dsn)

    detector = AlertDetector(
        rule_loader=rule_loader,
        alert_queue=alert_queue,
        stat_window_size=settings.stat_window_size,
        stat_zscore_threshold=settings.stat_zscore_threshold,
        ml_min_samples=settings.ml_min_samples,
        ml_refit_every=settings.ml_refit_every,
        ml_anomaly_threshold=settings.ml_anomaly_threshold,
    )

    mqtt_client = _connect_mqtt(settings)
    mqtt_client.on_message = detector.on_message
    mqtt_client.subscribe([("iiot/v1/telemetry/+/+/+/+", 1)])

    LOG.info(
        "alerting service started",
        extra={
            "event": {
                "dedup_window_sec": settings.dedup_window_sec,
                "stat_window": settings.stat_window_size,
                "ml_min_samples": settings.ml_min_samples,
            }
        },
    )

    while True:
        try:
            with psycopg.connect(settings.dsn) as conn:
                router = AlertRouter(
                    dsn=settings.dsn,
                    mqtt_client=mqtt_client,
                    rule_loader=rule_loader,
                    alert_queue=alert_queue,
                    dedup_window_sec=settings.dedup_window_sec,
                    webhook_url=settings.webhook_url,
                )
                while True:
                    router.drain(conn)
                    router.auto_close(conn)
                    time.sleep(0.2)
        except Exception as exc:
            LOG.warning("alerting loop failed, reconnecting", extra={"event": {"error": str(exc)}})
            time.sleep(2.0)


if __name__ == "__main__":
    run()
