from __future__ import annotations

import json
import queue
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.alerting.detector import AlertDetector
from services.alerting.rules import AlertRule, RuleLoader


def _make_msg(asset: str, signal: str, value: float, quality: str = "good") -> SimpleNamespace:
    topic = f"iiot/v1/telemetry/demo-site/line-1/{asset}/{signal}"
    payload = json.dumps(
        {
            "v": 2,
            "ts": 1730000000000,
            "source_ts": 1730000000000,
            "asset": asset,
            "signal": signal,
            "value": value,
            "quality": quality,
            "state": "RUNNING",
            "fault_code": 0,
            "seq": 1,
        }
    ).encode("utf-8")
    return SimpleNamespace(topic=topic, payload=payload)


def _make_rule(
    asset: str = "pump-01",
    signal: str = "temp",
    warn_low: float | None = None,
    warn_high: float | None = None,
    crit_low: float | None = None,
    crit_high: float | None = None,
) -> AlertRule:
    return AlertRule(
        id="00000000-0000-0000-0000-000000000001",
        asset=asset,
        signal=signal,
        warn_low=warn_low,
        warn_high=warn_high,
        crit_low=crit_low,
        crit_high=crit_high,
    )


def _make_detector(rule: AlertRule | None = None) -> tuple[AlertDetector, queue.Queue]:
    rule_loader = MagicMock(spec=RuleLoader)
    rule_loader.get.return_value = rule
    q: queue.Queue = queue.Queue()
    detector = AlertDetector(
        rule_loader=rule_loader,
        alert_queue=q,
        stat_window_size=100,
        stat_zscore_threshold=3.0,
        ml_min_samples=50,
        ml_refit_every=500,
        ml_anomaly_threshold=-0.1,
    )
    return detector, q


# ── Layer 1: threshold ───────────────────────────────────────────────────────


def test_threshold_fires_warn_low() -> None:
    rule = _make_rule(warn_low=5.0)
    detector, q = _make_detector(rule)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 3.0))
    assert not q.empty()
    alert = q.get_nowait()
    assert alert["alert_type"] == "threshold"
    assert alert["severity"] == "warning"
    assert alert["value"] == 3.0
    assert alert["threshold"] == 5.0


def test_threshold_fires_crit_high() -> None:
    rule = _make_rule(warn_high=80.0, crit_high=90.0)
    detector, q = _make_detector(rule)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 95.0))
    assert not q.empty()
    alert = q.get_nowait()
    assert alert["severity"] == "critical"
    assert alert["threshold"] == 90.0


def test_threshold_crit_takes_priority_over_warn() -> None:
    # Value violates both warn_high AND crit_high — crit must win
    rule = _make_rule(warn_high=70.0, crit_high=85.0)
    detector, q = _make_detector(rule)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 90.0))
    alert = q.get_nowait()
    assert alert["severity"] == "critical"


def test_threshold_no_alert_within_bounds() -> None:
    rule = _make_rule(warn_low=10.0, warn_high=80.0)
    detector, q = _make_detector(rule)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 50.0))
    assert q.empty()


def test_threshold_no_rule_no_alert() -> None:
    detector, q = _make_detector(rule=None)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 999.0))
    assert q.empty()


def test_bad_quality_skipped() -> None:
    rule = _make_rule(warn_high=10.0)
    detector, q = _make_detector(rule)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 999.0, quality="bad"))
    assert q.empty()


def test_stale_quality_skipped() -> None:
    rule = _make_rule(warn_high=10.0)
    detector, q = _make_detector(rule)
    detector.on_message(None, None, _make_msg("pump-01", "temp", 999.0, quality="stale"))
    assert q.empty()


# ── Layer 2: statistical ─────────────────────────────────────────────────────


def test_statistical_no_alert_too_few_samples() -> None:
    detector, q = _make_detector(rule=None)
    # Only 5 samples — below the 10-sample minimum
    for v in [50.0, 51.0, 49.0, 50.5, 50.2]:
        detector.on_message(None, None, _make_msg("pump-01", "pressure", v))
    assert q.empty()


def test_statistical_fires_on_spike() -> None:
    detector, q = _make_detector(rule=None)
    # Build a stable baseline around 50.0
    for v in [50.0] * 20:
        detector.on_message(None, None, _make_msg("pump-01", "pressure", v))
    # Inject a 10σ spike — should fire statistical alert
    detector.on_message(None, None, _make_msg("pump-01", "pressure", 500.0))
    assert not q.empty()
    alert = q.get_nowait()
    assert alert["alert_type"] == "statistical"
    assert alert["severity"] == "warning"


def test_statistical_no_alert_normal_variation() -> None:
    detector, q = _make_detector(rule=None)
    # Values with some natural variation — z-score should stay below 3.0
    base = [50.0 + (i % 5) * 0.1 for i in range(20)]
    for v in base:
        detector.on_message(None, None, _make_msg("pump-01", "pressure", v))
    # A slightly elevated reading that is not a spike
    detector.on_message(None, None, _make_msg("pump-01", "pressure", 50.5))
    assert q.empty()


# ── Layer 3: ML ──────────────────────────────────────────────────────────────


def test_ml_cold_start_no_alert() -> None:
    # Default min_samples=50 — with only 10 messages the scorer is not ready
    detector, q = _make_detector(rule=None)
    for i in range(10):
        detector.on_message(None, None, _make_msg("pump-01", "rpm", float(i)))
    # Scorer not ready yet — no ML alert possible
    scorer = detector._scorers.get(("pump-01", "rpm"))
    assert scorer is not None
    assert not scorer.ready
