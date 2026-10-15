from __future__ import annotations

import json
import logging
import math
import queue
from collections import deque
from typing import Any

import paho.mqtt.client as mqtt

from iiot_stack.telemetry import parse_telemetry_topic

from .models.anomaly import AnomalyScorer
from .rules import AlertRule, RuleLoader

LOG = logging.getLogger("alerting.detector")


class AlertDetector:
    """
    Subscribes to MQTT telemetry and runs 3 detection layers on every message.

    Layer 1 — Threshold:    compare value against operator-configured alert_rules
    Layer 2 — Statistical:  z-score against a per-signal rolling baseline
    Layer 3 — ML anomaly:   IsolationForest per signal (activates after min_samples)

    Detected alerts are pushed as dicts to alert_queue for the router to process.
    Layers are evaluated in priority order; if Layer 1 fires, Layers 2/3 are skipped
    to avoid alert noise from multiple simultaneous triggers on the same condition.

    Only 'good' quality samples are processed — bad/stale quality would corrupt
    the statistical baseline and produce false positives during fault conditions.
    """

    def __init__(
        self,
        rule_loader: RuleLoader,
        alert_queue: queue.Queue[dict[str, Any]],
        stat_window_size: int = 100,
        stat_zscore_threshold: float = 3.0,
        ml_min_samples: int = 50,
        ml_refit_every: int = 500,
        ml_anomaly_threshold: float = -0.1,
    ) -> None:
        self._rules = rule_loader
        self._queue = alert_queue
        self._stat_window_size = stat_window_size
        self._stat_zscore_threshold = stat_zscore_threshold
        self._ml_min_samples = ml_min_samples
        self._ml_refit_every = ml_refit_every
        self._ml_anomaly_threshold = ml_anomaly_threshold
        # Per-(asset, signal) rolling windows for Layer 2
        self._windows: dict[tuple[str, str], deque[float]] = {}
        # Per-(asset, signal) AnomalyScorers for Layer 3
        self._scorers: dict[tuple[str, str], AnomalyScorer] = {}

    def on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            site, line, asset, signal = parse_telemetry_topic(msg.topic)
            value = float(payload["value"])
            quality = str(payload.get("quality", "good"))
        except Exception as exc:
            LOG.debug("skipping unparseable message", extra={"event": {"error": str(exc)}})
            return

        # Noisy / unreliable readings would corrupt baselines
        if quality != "good":
            return

        key = (asset, signal)
        self._update_baselines(key, value)

        alert = (
            self._check_threshold(asset, signal, value)
            or self._check_statistical(key, asset, signal, value)
            or self._check_ml(key, asset, signal, value)
        )
        if alert:
            self._queue.put({**alert, "site": site, "line_name": line})

    # ── baseline updaters ────────────────────────────────────────────────────

    def _update_baselines(self, key: tuple[str, str], value: float) -> None:
        if key not in self._windows:
            self._windows[key] = deque(maxlen=self._stat_window_size)
        self._windows[key].append(value)

        if key not in self._scorers:
            self._scorers[key] = AnomalyScorer(
                min_samples=self._ml_min_samples,
                refit_every=self._ml_refit_every,
                threshold=self._ml_anomaly_threshold,
            )
        self._scorers[key].add(value)

    # ── detection layers ─────────────────────────────────────────────────────

    def _check_threshold(self, asset: str, signal: str, value: float) -> dict[str, Any] | None:
        rule: AlertRule | None = self._rules.get(asset, signal)
        if rule is None:
            return None

        # Critical band takes precedence over warning band
        if rule.crit_low is not None and value < rule.crit_low:
            return _make_alert(
                "threshold",
                "critical",
                asset,
                signal,
                value,
                rule.crit_low,
                f"{signal} {value:.3g} below critical low {rule.crit_low:.3g}",
                rule.id,
            )
        if rule.crit_high is not None and value > rule.crit_high:
            return _make_alert(
                "threshold",
                "critical",
                asset,
                signal,
                value,
                rule.crit_high,
                f"{signal} {value:.3g} above critical high {rule.crit_high:.3g}",
                rule.id,
            )
        if rule.warn_low is not None and value < rule.warn_low:
            return _make_alert(
                "threshold",
                "warning",
                asset,
                signal,
                value,
                rule.warn_low,
                f"{signal} {value:.3g} below warning low {rule.warn_low:.3g}",
                rule.id,
            )
        if rule.warn_high is not None and value > rule.warn_high:
            return _make_alert(
                "threshold",
                "warning",
                asset,
                signal,
                value,
                rule.warn_high,
                f"{signal} {value:.3g} above warning high {rule.warn_high:.3g}",
                rule.id,
            )
        return None

    def _check_statistical(
        self,
        key: tuple[str, str],
        asset: str,
        signal: str,
        value: float,
    ) -> dict[str, Any] | None:
        window = self._windows.get(key)
        if window is None or len(window) < 10:
            return None  # not enough history for a meaningful baseline

        samples = list(window)
        n = len(samples)
        mean = sum(samples) / n
        variance = sum((x - mean) ** 2 for x in samples) / n
        std = math.sqrt(variance)

        if std < 1e-9:
            return None  # flat signal — z-score undefined

        z = abs(value - mean) / std
        if z > self._stat_zscore_threshold:
            return _make_alert(
                "statistical",
                "warning",
                asset,
                signal,
                value,
                None,
                f"{signal} z-score {z:.1f}σ (mean={mean:.3g}, std={std:.3g})",
                None,
            )
        return None

    def _check_ml(
        self,
        key: tuple[str, str],
        asset: str,
        signal: str,
        value: float,
    ) -> dict[str, Any] | None:
        scorer = self._scorers.get(key)
        if scorer is None or not scorer.is_anomaly(value):
            return None
        score = scorer.score(value)
        return _make_alert(
            "ml",
            "warning",
            asset,
            signal,
            value,
            None,
            f"{signal} ML anomaly score {score:.3f}",
            None,
        )


def _make_alert(
    alert_type: str,
    severity: str,
    asset: str,
    signal: str,
    value: float,
    threshold: float | None,
    message: str,
    rule_id: str | None,
) -> dict[str, Any]:
    return {
        "asset": asset,
        "signal": signal,
        "alert_type": alert_type,
        "severity": severity,
        "value": value,
        "threshold": threshold,
        "message": message,
        "rule_id": rule_id,
    }
