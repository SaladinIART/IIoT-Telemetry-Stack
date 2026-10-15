from __future__ import annotations

import queue
import time
from unittest.mock import MagicMock

from services.alerting.router import AlertRouter, _value_in_bounds
from services.alerting.rules import AlertRule, RuleLoader


def _make_alert(
    asset: str = "pump-01",
    signal: str = "temp",
    alert_type: str = "threshold",
    severity: str = "warning",
    value: float = 95.0,
    threshold: float | None = 90.0,
    rule_id: str | None = "00000000-0000-0000-0000-000000000001",
) -> dict:
    return {
        "site": "demo-site",
        "line_name": "line-1",
        "asset": asset,
        "signal": signal,
        "alert_type": alert_type,
        "severity": severity,
        "value": value,
        "threshold": threshold,
        "message": f"{signal} exceeded threshold",
        "rule_id": rule_id,
    }


def _make_router(dedup_window_sec: float = 300.0) -> tuple[AlertRouter, queue.Queue]:
    rule_loader = MagicMock(spec=RuleLoader)
    mqtt_client = MagicMock()
    q: queue.Queue = queue.Queue()
    router = AlertRouter(
        dsn="host=localhost dbname=iiot user=iiot password=test",
        mqtt_client=mqtt_client,
        rule_loader=rule_loader,
        alert_queue=q,
        dedup_window_sec=dedup_window_sec,
        webhook_url="",
    )
    return router, q


def _mock_cursor_returning(alert_id: str = "abc-123") -> MagicMock:
    """Return a mock cursor whose fetchone() returns (alert_id, <datetime-like>)."""
    opened_at = MagicMock()
    opened_at.timestamp.return_value = 1730000000.0
    cur = MagicMock()
    cur.fetchone.return_value = (alert_id, opened_at)
    return cur


# ── deduplication ────────────────────────────────────────────────────────────


def test_dedup_suppresses_second_alert_within_window() -> None:
    router, q = _make_router(dedup_window_sec=300.0)
    cur = _mock_cursor_returning()
    alert = _make_alert()

    q.put(alert)
    q.put(alert)  # immediate duplicate

    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    router.drain(conn)
    # Only one INSERT should have been executed
    assert cur.execute.call_count == 1


def test_dedup_allows_alert_after_window_expires() -> None:
    router, q = _make_router(dedup_window_sec=0.01)  # 10ms window
    cur = _mock_cursor_returning()
    alert = _make_alert()

    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    q.put(alert)
    router.drain(conn)
    assert cur.execute.call_count == 1

    time.sleep(0.05)  # let the window expire

    q.put(alert)
    router.drain(conn)
    # Second drain should also insert (window has expired)
    assert cur.execute.call_count == 2


def test_dedup_different_signal_not_suppressed() -> None:
    router, q = _make_router()
    cur = _mock_cursor_returning()
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    q.put(_make_alert(signal="temp"))
    q.put(_make_alert(signal="pressure"))  # different signal — must not be deduped

    router.drain(conn)
    assert cur.execute.call_count == 2


def test_dedup_different_alert_type_not_suppressed() -> None:
    router, q = _make_router()
    cur = _mock_cursor_returning()
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = lambda s: cur
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    q.put(_make_alert(alert_type="threshold"))
    q.put(_make_alert(alert_type="statistical"))  # different type — separate dedup key

    router.drain(conn)
    assert cur.execute.call_count == 2


# ── _value_in_bounds ─────────────────────────────────────────────────────────


def _rule(**kwargs) -> AlertRule:
    defaults = dict(
        id="00000000-0000-0000-0000-000000000001",
        asset="pump-01",
        signal="temp",
        warn_low=None,
        warn_high=None,
        crit_low=None,
        crit_high=None,
    )
    return AlertRule(**{**defaults, **kwargs})


def test_value_in_bounds_no_limits() -> None:
    rule = _rule()
    assert _value_in_bounds(999.0, rule) is True


def test_value_in_bounds_within_warn() -> None:
    rule = _rule(warn_low=10.0, warn_high=80.0)
    assert _value_in_bounds(50.0, rule) is True


def test_value_out_of_bounds_crit_high() -> None:
    rule = _rule(crit_high=90.0)
    assert _value_in_bounds(91.0, rule) is False


def test_value_out_of_bounds_warn_low() -> None:
    rule = _rule(warn_low=5.0)
    assert _value_in_bounds(3.0, rule) is False


def test_value_exactly_at_boundary_not_triggered() -> None:
    # Boundary values are NOT violations (> and < are strict)
    rule = _rule(warn_high=80.0, crit_low=5.0)
    assert _value_in_bounds(80.0, rule) is True
    assert _value_in_bounds(5.0, rule) is True
