"""GET /api/v1/dashboard — Executive summary for the management demo.

Aggregates asset states, business impact, maintenance status, and order risk
into a single response designed for the Executive Dashboard frontend page.
"""

from __future__ import annotations

import os
from typing import Annotated

import httpx
import psycopg
from fastapi import APIRouter, Depends

from services.api.dependencies import get_conn, require_api_key
from services.api.schemas.dashboard import (
    AssetSummaryForDashboard,
    DashboardResponse,
    FinancialSummary,
    LogisticsStatus,
    MaintenanceStatus,
    OrderSummary,
    ProductionStatus,
    RecommendedAction,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

# Where the modbus_sim scenario API lives (override via env var for local dev)
_SIM_BASE = os.getenv("MODBUS_SIM_API", "http://modbus-sim:5001")

# MTTR estimates per fault code (minutes) — informed by maintenance_log history.
# Keys match fault_map values in contracts/register_map.json.
_MTTR_MAP = {
    111: 60,  # furnace OVER_TEMPERATURE    — recalibrate zone thermocouples
    112: 45,  # furnace UNDER_TEMPERATURE   — recover setpoint
    113: 240,  # furnace BURNER_TRIP         — igniter/burner inspection
    211: 120,  # press EXTRUSION_OVERLOAD    — die inspection / regrind
    212: 60,  # press BILLET_JAM            — clear + alignment check
    219: 300,  # press EMERGENCY_TRIP        — full safety interlock cycle
    311: 30,  # quench QUENCH_FLOW_LOW      — strainer / nozzle clean
    312: 45,  # quench QUENCH_TEMP_HIGH     — chiller coil check
    411: 30,  # cooling TABLE_HOT           — clear blocked air intake
    412: 45,  # cooling AIR_FLOW_LOW        — filter replace
    511: 30,  # stretcher SLIP              — jaw reface
    512: 60,  # stretcher FORCE_HIGH        — load cell recal
    611: 45,  # saw BLADE_WEAR              — blade change
    612: 30,  # saw CUT_LENGTH_DEVIATION    — encoder/gauge calibration
    711: 90,  # ageing AGE_TEMP_DEVIATION   — heater element / circulation
    712: 60,  # ageing AGE_DWELL_SHORT      — door seal / dwell timer
}

# Mapped from decision_board_rules.owner → RecommendedAction.owner (normalised uppercase enum)
_OWNER_TO_ENUM = {
    "Plant Manager": "MANAGEMENT",
    "Shift Supervisor": "MANAGEMENT",
    "Quality": "PRODUCTION",
    "Maintenance": "MAINTENANCE",
    "Operator": "PRODUCTION",
    "Logistics": "LOGISTICS",
}

# Priority (P1/P2/P3) → urgency enum expected by RecommendedAction schema
_PRIORITY_TO_URGENCY = {
    "P1": "IMMEDIATE",
    "P2": "URGENT",
    "P3": "SOON",
}

# Python fallback used only when the SQL decision view returns zero rows (e.g. DB hiccup
# or a scenario name that hasn't been seeded yet). Keeps the schema valid.
_FALLBACK_ACTIONS: dict[str, list[dict]] = {
    "NORMAL": [
        {
            "urgency": "INFO",
            "owner": "MANAGEMENT",
            "action": "All systems nominal — continue planned production run.",
        },
    ],
    "QUALITY_HOLD_QUENCH": [
        {
            "urgency": "URGENT",
            "owner": "PRODUCTION",
            "action": "Quench flow anomaly — check Decision Board in Grafana.",
        },
    ],
    "PRESS_BOTTLENECK": [
        {
            "urgency": "IMMEDIATE",
            "owner": "MAINTENANCE",
            "action": "Press overload — dispatch maintenance, check Decision Board.",
        },
    ],
    "STRETCHER_BACKLOG": [
        {
            "urgency": "URGENT",
            "owner": "MAINTENANCE",
            "action": "Stretcher offline — check Decision Board in Grafana.",
        },
    ],
    "AGEING_OVEN_DEVIATION": [
        {
            "urgency": "URGENT",
            "owner": "PRODUCTION",
            "action": "Ageing oven out of spec — check Decision Board in Grafana.",
        },
    ],
    "EMERGENCY_PRESS_TRIP": [
        {
            "urgency": "IMMEDIATE",
            "owner": "MANAGEMENT",
            "action": "Press emergency trip — invoke BCP immediately.",
        },
    ],
}

_ASSET_ICONS = {
    "furnace": "homogenisation_furnace",
    "press": "extrusion_press",
    "quench": "water_quench",
    "cooling": "cooling_table",
    "stretcher": "profile_stretcher",
    "saw": "finish_saw",
    "ageing": "ageing_oven",
}

_ASSET_SQL = """
SELECT
    b.asset,
    b.display_name,
    a.asset_type,
    b.state,
    b.fault_code,
    b.cost_rate_myr_hr,
    b.cost_so_far_myr,
    m.last_maint_at,
    m.pm_risk
FROM v_business_impact b
JOIN v_asset_current_state a ON a.asset = b.asset
LEFT JOIN v_maintenance_status m ON m.asset = b.asset
ORDER BY b.asset
"""

_ORDER_SQL = """
SELECT
    id, customer, quantity_ordered, due_at,
    order_value_myr, computed_status
FROM v_order_risk
ORDER BY due_at
"""

_PROFILES_SHIPPED_TODAY_SQL = """
SELECT COALESCE(
    MAX(value::bigint) - MIN(value::bigint), 0
) AS profiles_shipped_today
FROM telemetry
WHERE asset = 'ageing-01'
  AND signal = 'aged_batch_count'
  AND ts >= date_trunc('day', NOW() AT TIME ZONE 'Asia/Kuala_Lumpur') AT TIME ZONE 'Asia/Kuala_Lumpur'
"""

_DECISION_BOARD_SQL = """
SELECT priority, owner, action_text
FROM v_aluminium_decision_board
LIMIT 6
"""

_SCHEDULE_SQL = """
SELECT target_units
FROM production_schedule
WHERE shift_date = CURRENT_DATE
  AND shift_name = 'Morning'
LIMIT 1
"""


def _get_scenario() -> dict:
    try:
        resp = httpx.get(f"{_SIM_BASE}/scenario", timeout=2.0)
        return resp.json()
    except Exception:
        return {"scenario": "NORMAL", "health": "GREEN", "message": "Scenario API unavailable"}


@router.get("", response_model=DashboardResponse, dependencies=[Depends(require_api_key)])
def get_dashboard(conn: Annotated[psycopg.Connection, Depends(get_conn)]) -> DashboardResponse:
    scenario_info = _get_scenario()
    scenario = scenario_info.get("scenario", "NORMAL")
    health = scenario_info.get("health", "GREEN")
    health_message = scenario_info.get("message", "")

    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        # Assets + business impact
        cur.execute(_ASSET_SQL)
        asset_rows = cur.fetchall()

        # Orders
        cur.execute(_ORDER_SQL)
        order_rows = cur.fetchall()

        # Production
        cur.execute(_PROFILES_SHIPPED_TODAY_SQL)
        shipped_row = cur.fetchone()
        cur.execute(_SCHEDULE_SQL)
        schedule_row = cur.fetchone()

        # Decision board (single source of truth — same view Grafana reads)
        cur.execute(_DECISION_BOARD_SQL)
        decision_rows = cur.fetchall()

    # ── Financial ──────────────────────────────────────────────────────────────
    total_cost_rate = sum(float(r["cost_rate_myr_hr"] or 0) for r in asset_rows)
    total_cost_so_far = sum(float(r["cost_so_far_myr"] or 0) for r in asset_rows)

    at_risk_orders = [o for o in order_rows if o["computed_status"] in ("AT_RISK", "DELAYED")]
    at_risk_value = sum(float(o["order_value_myr"] or 0) for o in at_risk_orders)

    financial = FinancialSummary(
        cost_rate_myr_hr=round(total_cost_rate, 2),
        cost_so_far_myr=round(total_cost_so_far, 2),
        orders_at_risk_count=len(at_risk_orders),
        orders_at_risk_value_myr=round(at_risk_value, 2),
    )

    # ── Recommended actions (SQL-first, Python fallback) ──────────────────────
    if decision_rows:
        recommended_actions = [
            RecommendedAction(
                urgency=_PRIORITY_TO_URGENCY.get(row["priority"], "SOON"),
                owner=_OWNER_TO_ENUM.get(row["owner"], "MANAGEMENT"),
                action=row["action_text"],
            )
            for row in decision_rows
        ]
    else:
        fallback = _FALLBACK_ACTIONS.get(scenario, _FALLBACK_ACTIONS["NORMAL"])
        recommended_actions = [RecommendedAction(**a) for a in fallback]

    # ── Production ────────────────────────────────────────────────────────────
    faulted = [r for r in asset_rows if r["state"] in ("FAULTED", "MAINTENANCE")]
    units_today = int(shipped_row["profiles_shipped_today"]) if shipped_row else 0
    target_today = int(schedule_row["target_units"]) if schedule_row else 320

    # Rough throughput estimate: if any machine faulted → proportional reduction
    running_count = sum(1 for r in asset_rows if r["state"] == "RUNNING")
    throughput_pct = round((running_count / max(len(asset_rows), 1)) * 100, 1)

    production = ProductionStatus(
        throughput_pct=throughput_pct,
        units_today=units_today,
        target_today=target_today,
        faulted_machine_count=len(faulted),
    )

    # ── Maintenance ───────────────────────────────────────────────────────────
    healthy = sum(
        1
        for r in asset_rows
        if r["state"] not in ("FAULTED", "MAINTENANCE") and r.get("pm_risk") == "LOW"
    )
    at_risk_pm = sum(
        1
        for r in asset_rows
        if r.get("pm_risk") in ("MEDIUM", "HIGH") and r["state"] not in ("FAULTED", "MAINTENANCE")
    )

    # Estimate MTTR from the worst active fault code
    mttr_estimate = None
    for r in faulted:
        fc = int(r["fault_code"] or 0)
        est = _MTTR_MAP.get(fc)
        if est:
            mttr_estimate = max(mttr_estimate or 0, est)

    maintenance_status = MaintenanceStatus(
        machines_healthy=healthy,
        machines_at_risk=at_risk_pm,
        machines_faulted=len(faulted),
        current_mttr_estimate_min=mttr_estimate,
    )

    # ── Logistics ─────────────────────────────────────────────────────────────
    on_track = sum(1 for o in order_rows if o["computed_status"] in ("ON_TRACK",))
    monitoring = sum(1 for o in order_rows if o["computed_status"] == "MONITORING")
    at_risk_count = sum(1 for o in order_rows if o["computed_status"] == "AT_RISK")
    delayed_count = sum(1 for o in order_rows if o["computed_status"] == "DELAYED")

    upcoming = sorted(order_rows, key=lambda o: o["due_at"])
    next_order = upcoming[0] if upcoming else None

    orders_out = [
        OrderSummary(
            id=o["id"],
            customer=o["customer"],
            quantity_ordered=o["quantity_ordered"],
            due_at=o["due_at"],
            order_value_myr=float(o["order_value_myr"] or 0),
            computed_status=o["computed_status"],
        )
        for o in order_rows
    ]

    logistics = LogisticsStatus(
        orders_on_track=on_track,
        orders_monitoring=monitoring,
        orders_at_risk=at_risk_count,
        orders_delayed=delayed_count,
        next_deadline_at=next_order["due_at"] if next_order else None,
        next_deadline_customer=next_order["customer"] if next_order else None,
        orders=orders_out,
    )

    # ── Assets list ───────────────────────────────────────────────────────────
    assets_out = [
        AssetSummaryForDashboard(
            asset=r["asset"],
            display_name=r["display_name"],
            asset_type=r["asset_type"],
            state=r["state"],
            fault_code=int(r["fault_code"] or 0),
            cost_rate_myr_hr=float(r["cost_rate_myr_hr"] or 0),
            cost_so_far_myr=float(r["cost_so_far_myr"] or 0),
            last_maint_at=r.get("last_maint_at"),
            pm_risk=r.get("pm_risk"),
        )
        for r in asset_rows
    ]

    return DashboardResponse(
        scenario=scenario,
        health=health,
        health_message=health_message,
        financial=financial,
        recommended_actions=recommended_actions,
        production=production,
        maintenance=maintenance_status,
        logistics=logistics,
        assets=assets_out,
    )
