from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import psycopg

LOG = logging.getLogger("alerting.rules")

_LOAD_SQL = (
    "SELECT id::text, asset, signal, warn_low, warn_high, crit_low, crit_high "
    "FROM alert_rules WHERE enabled = TRUE"
)


@dataclass(frozen=True)
class AlertRule:
    id: str
    asset: str
    signal: str
    warn_low: float | None
    warn_high: float | None
    crit_low: float | None
    crit_high: float | None


class RuleLoader:
    """
    Loads enabled alert_rules from TimescaleDB and caches them in memory.
    Refreshes automatically every refresh_interval_s seconds.

    Stale rules are kept on DB failure rather than cleared, so the detector
    continues operating with the last known configuration.
    """

    def __init__(self, dsn: str, refresh_interval_s: float = 60.0) -> None:
        self._dsn = dsn
        self._refresh_interval_s = refresh_interval_s
        self._rules: dict[tuple[str, str], AlertRule] = {}
        self._last_load: float = 0.0

    def get(self, asset: str, signal: str) -> AlertRule | None:
        """Return the rule for (asset, signal), refreshing the cache if due."""
        self._refresh_if_due()
        return self._rules.get((asset, signal))

    def all_rules(self) -> dict[tuple[str, str], AlertRule]:
        """Return all enabled rules, refreshing the cache if due."""
        self._refresh_if_due()
        return self._rules

    def _refresh_if_due(self) -> None:
        if time.time() - self._last_load >= self._refresh_interval_s:
            self._load()

    def _load(self) -> None:
        try:
            with psycopg.connect(self._dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(_LOAD_SQL)
                    rows = cur.fetchall()
            self._rules = {
                (row[1], row[2]): AlertRule(
                    id=row[0],
                    asset=row[1],
                    signal=row[2],
                    warn_low=float(row[3]) if row[3] is not None else None,
                    warn_high=float(row[4]) if row[4] is not None else None,
                    crit_low=float(row[5]) if row[5] is not None else None,
                    crit_high=float(row[6]) if row[6] is not None else None,
                )
                for row in rows
            }
            self._last_load = time.time()
            LOG.info("rules reloaded", extra={"event": {"count": len(self._rules)}})
        except Exception as exc:
            # Keep stale rules — better to alert on old thresholds than to stop alerting
            LOG.warning(
                "rule reload failed, keeping stale rules", extra={"event": {"error": str(exc)}}
            )
            self._last_load = time.time()
