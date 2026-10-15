"""Generate PLACEHOLDER demo fixtures so the browser demo can be built and tested
without a running Docker stack.

These are NOT captured from the pipeline. The manifest says
``"source": "placeholder"`` and the demo UI shows a visible notice until
``tools/capture_demo_fixtures.py`` replaces them with real output.

Shapes mirror services/api/schemas; scenario definitions are imported from the
simulator so states and fault codes cannot drift.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim" / "modbus_sim"))
import scenario_state as ss  # noqa: E402

DEFAULT_OUT = ROOT / "frontend" / "demo-fixtures"
STATE_NAMES = {0: "IDLE", 1: "STARTUP", 2: "RUNNING", 3: "FAULTED", 4: "MAINTENANCE"}
COST_RATE = {"press": 4200.0, "quench": 1800.0, "furnace": 2600.0, "ageing": 1500.0}
ORDERS = [
    ("PO-AL-2024-0018", "MNC Customer A", 2000, 48, 84000.0),
    ("PO-AL-2024-0021", "Automotive Customer B", 800, 28, 76000.0),
    ("PO-AL-2024-0025", "Building Systems Customer C", 1500, 120, 87000.0),
]
ACTIONS = {
    "NORMAL": [("INFO", "MANAGEMENT", "All systems nominal - continue planned production run.")],
    "QUALITY_HOLD_QUENCH": [
        ("URGENT", "PRODUCTION", "Place in-box batch on P2 quality hold - quench flow below spec."),
        ("URGENT", "MAINTENANCE", "Dispatch to quench-01 - inspect spray nozzles and strainer."),
        (
            "URGENT",
            "LOGISTICS",
            "Notify Automotive Customer B of potential delay on PO-AL-2024-0021.",
        ),
    ],
    "PRESS_BOTTLENECK": [
        (
            "IMMEDIATE",
            "MAINTENANCE",
            "Press overload - inspect die and regrind, downstream is starved.",
        ),
        ("URGENT", "LOGISTICS", "Re-plan order sequence while the press is down."),
    ],
    "STRETCHER_BACKLOG": [
        ("URGENT", "MAINTENANCE", "Stretcher in maintenance - complete grip change to clear WIP."),
        ("SOON", "PRODUCTION", "Slow billet feed to limit cooling-table accumulation."),
    ],
    "AGEING_OVEN_DEVIATION": [
        ("URGENT", "PRODUCTION", "Hold in-flight ageing batch for T6 retest."),
        ("URGENT", "MAINTENANCE", "Inspect heater elements and air circulation on ageing-01."),
    ],
    "EMERGENCY_PRESS_TRIP": [
        ("IMMEDIATE", "MANAGEMENT", "Press emergency trip - invoke business continuity plan."),
        ("IMMEDIATE", "MAINTENANCE", "Full safety interlock cycle before restart."),
        ("URGENT", "LOGISTICS", "All three customer orders at risk - notify account managers."),
    ],
}


def load_assets() -> list[dict]:
    reg = json.loads((ROOT / "contracts" / "register_map.json").read_text(encoding="utf-8"))
    return reg["assets"]


def display_names() -> dict[str, str]:
    return {
        "furnace-01": "Homogenisation Furnace",
        "press-01": "Extrusion Press",
        "quench-01": "Water Quench",
        "cooling-01": "Cooling Table",
        "stretcher-01": "Profile Stretcher",
        "saw-01": "Finish Saw",
        "ageing-01": "Ageing Oven",
    }


def build(scenario: str, assets: list[dict], now: datetime, rng: random.Random) -> dict:
    names = display_names()
    states = ss.SCENARIO_STATES[scenario]
    health = ss.SCENARIO_HEALTH[scenario]
    ts = now.isoformat()
    out_assets, dash_assets, alerts, telemetry = [], [], [], {}
    faulted = 0
    for a in assets:
        aid = a["asset_id"]
        state, fault = states[aid]
        state_name = STATE_NAMES[state]
        is_fault = state == 3
        faulted += is_fault
        sites = {"site": "demo-site", "line_name": "aluminium-profile-line-1"}
        open_alerts = 1 if is_fault else 0
        out_assets.append(
            {
                "asset": aid,
                "display_name": names[aid],
                "asset_type": a["asset_type"],
                **sites,
                "cell_name": a["cell"],
                "state": state_name,
                "fault_code": fault,
                "quality": "BAD" if is_fault else "GOOD",
                "last_seen": ts,
                "open_alert_count": open_alerts,
            }
        )
        rate = COST_RATE.get(a["asset_type"], 1000.0) if is_fault else 0.0
        dash_assets.append(
            {
                "asset": aid,
                "display_name": names[aid],
                "asset_type": a["asset_type"],
                "state": state_name,
                "fault_code": fault,
                "cost_rate_myr_hr": rate,
                "cost_so_far_myr": round(rate * 0.4, 2),
                "last_maint_at": (now - timedelta(days=9)).isoformat(),
                "pm_risk": "HIGH" if is_fault else "LOW",
            }
        )
        analog = [s for s in a["signals"] if s.get("signal_class") == "analog"]
        series = []
        for sig in analog:
            lim = sig.get("limits", {})
            lo, hi = lim.get("warn_low"), lim.get("warn_high")
            mid = (lo + hi) / 2 if lo is not None and hi is not None else (lo or hi or 50.0)
            span = (hi - lo) / 6 if lo is not None and hi is not None else abs(mid) * 0.02
            if state == 0:
                mid *= 0.4
            for i in range(60):
                t = now - timedelta(seconds=2 * (59 - i))
                v = mid + span * math.sin(i / 7) + rng.uniform(-span, span) * 0.3
                if is_fault and i > 40 and hi is not None:
                    v = hi + span * (i - 40) / 6
                series.append(
                    {
                        "ts": t.isoformat(),
                        "asset": aid,
                        "signal": sig["tag_id"],
                        "value": round(v, 2),
                        "quality": "GOOD",
                        "state": state_name,
                    }
                )
        telemetry[aid] = series
        if is_fault and analog:
            sig = analog[0]
            alerts.append(
                {
                    "id": f"00000000-0000-4000-8000-{len(alerts):012d}",
                    "opened_at": ts,
                    "site": "demo-site",
                    "line_name": "aluminium-profile-line-1",
                    "asset": aid,
                    "asset_display_name": names[aid],
                    "signal": sig["tag_id"],
                    "alert_type": "threshold",
                    "severity": "critical",
                    "value": series[-1]["value"] if series else 0.0,
                    "threshold": sig.get("limits", {}).get("warn_high"),
                    "state": "OPEN",
                    "message": f"{names[aid]} fault {fault}: {ss.SCENARIO_MESSAGES[scenario]}",
                    "acked_at": None,
                    "closed_at": None,
                    "rule_id": None,
                }
            )
    running = sum(1 for s in states.values() if s[0] == 2)
    at_risk = 0 if scenario == "NORMAL" else (3 if scenario == "EMERGENCY_PRESS_TRIP" else 1)
    dash = {
        "scenario": scenario,
        "health": health,
        "health_message": ss.SCENARIO_MESSAGES[scenario],
        "financial": {
            "cost_rate_myr_hr": sum(x["cost_rate_myr_hr"] for x in dash_assets),
            "cost_so_far_myr": sum(x["cost_so_far_myr"] for x in dash_assets),
            "orders_at_risk_count": at_risk,
            "orders_at_risk_value_myr": sum(o[4] for o in ORDERS[:at_risk]),
        },
        "recommended_actions": [
            {"urgency": u, "owner": o, "action": t} for u, o, t in ACTIONS[scenario]
        ],
        "production": {
            "throughput_pct": round(100.0 * running / len(states), 1),
            "units_today": 1240,
            "target_today": 2000,
            "faulted_machine_count": faulted,
        },
        "maintenance": {
            "machines_healthy": running,
            "machines_at_risk": 0,
            "machines_faulted": faulted,
            "current_mttr_estimate_min": 60 if faulted else None,
        },
        "logistics": {
            "orders_on_track": len(ORDERS) - at_risk,
            "orders_monitoring": 0,
            "orders_at_risk": at_risk,
            "orders_delayed": 0,
            "next_deadline_at": (now + timedelta(hours=28)).isoformat(),
            "next_deadline_customer": ORDERS[1][1],
            "orders": [
                {
                    "id": oid,
                    "customer": cust,
                    "quantity_ordered": qty,
                    "due_at": (now + timedelta(hours=h)).isoformat(),
                    "order_value_myr": val,
                    "computed_status": "AT_RISK" if i < at_risk else "ON_TRACK",
                }
                for i, (oid, cust, qty, h, val) in enumerate(ORDERS)
            ],
        },
        "assets": dash_assets,
    }
    kpis = [
        {
            "asset": x["asset"],
            "display_name": x["display_name"],
            "asset_type": x["asset_type"],
            "window_hours": 8.0,
            "total_readings": 28800,
            "good_readings": 28800 if x["state"] != "FAULTED" else 26900,
            "quality_rate": 1.0 if x["state"] != "FAULTED" else 0.934,
            "running_minutes": 480.0 if x["state"] == "RUNNING" else 380.0,
            "fault_minutes": 0.0 if x["state"] != "FAULTED" else 40.0,
            "availability": 1.0 if x["state"] != "FAULTED" else 0.79,
            "open_alert_count": 1 if x["state"] == "FAULTED" else 0,
        }
        for x in out_assets
    ]
    return {
        "scenario.json": {**ss.status(), "scenario": scenario},
        "dashboard.json": dash,
        "assets.json": out_assets,
        "alerts.json": alerts,
        "kpis.json": kpis,
        "telemetry": telemetry,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    now = datetime.now(UTC).replace(microsecond=0)
    rng = random.Random(20261015)
    assets = load_assets()
    for scenario in ss.SCENARIO_STATES:
        built = build(scenario, assets, now, rng)
        folder = args.output / scenario
        for name, payload in built.items():
            if name == "telemetry":
                for aid, series in payload.items():
                    p = folder / "telemetry" / f"{aid}.json"
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(json.dumps(series, indent=1) + "\n", encoding="utf-8")
            else:
                (folder).mkdir(parents=True, exist_ok=True)
                (folder / name).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "sites.json").write_text(
        json.dumps(
            [
                {
                    "site_id": "demo-site",
                    "display_name": "Demo Aluminium Plant",
                    "location": "Simulated",
                    "timezone": "Asia/Kuala_Lumpur",
                    "active": True,
                }
            ],
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output / "manifest.json").write_text(
        json.dumps(
            {
                "source": "placeholder",
                "generated_at": now.isoformat(),
                "note": "Not captured from the live pipeline; run tools/capture_demo_fixtures.py.",
                "scenarios": [{"scenario": s} for s in ss.SCENARIO_STATES],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"placeholder fixtures -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
