"""Shared in-memory scenario state for the Modbus simulator.

The scenario_api Flask endpoint writes here; the Modbus updater thread reads here.
All access is protected by a single threading.Lock for thread safety.
"""

from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_scenario: str = "NORMAL"
_expires_at: float = 0.0  # epoch seconds; 0 = pinned indefinitely

# ─── Scenario definitions ──────────────────────────────────────────────────────
# Aluminium Profile Line 1 — 7 stations, 6 scenarios.
# Each entry maps asset_id → (state_code, fault_code)
# State codes: 0=IDLE, 1=STARTUP, 2=RUNNING, 3=FAULTED, 4=MAINTENANCE
SCENARIO_STATES: dict[str, dict[str, tuple[int, int]]] = {
    "NORMAL": {
        "furnace-01": (2, 0),
        "press-01": (2, 0),
        "quench-01": (2, 0),
        "cooling-01": (2, 0),
        "stretcher-01": (2, 0),
        "saw-01": (2, 0),
        "ageing-01": (2, 0),
    },
    "QUALITY_HOLD_QUENCH": {
        # Flagship scenario — quench flow drops, exit temperature rises.
        # T5/T6 temper at risk on profiles in the box during deviation.
        "furnace-01": (2, 0),
        "press-01": (2, 0),
        "quench-01": (3, 311),  # QUENCH_FLOW_LOW
        "cooling-01": (2, 0),
        "stretcher-01": (2, 0),
        "saw-01": (2, 0),
        "ageing-01": (2, 0),
    },
    "PRESS_BOTTLENECK": {
        # Extrusion overload halts the heart of the line.
        # Furnace still loading billets; downstream goes idle waiting for profiles.
        "furnace-01": (1, 0),  # STARTUP — billets warm but not advancing
        "press-01": (3, 211),  # EXTRUSION_OVERLOAD
        "quench-01": (0, 0),
        "cooling-01": (0, 0),
        "stretcher-01": (0, 0),
        "saw-01": (0, 0),
        "ageing-01": (0, 0),
    },
    "STRETCHER_BACKLOG": {
        # Stretcher offline for grip change — WIP piling up on cooling table.
        "furnace-01": (2, 0),
        "press-01": (2, 0),
        "quench-01": (2, 0),
        "cooling-01": (2, 0),  # still receiving, backlog growing
        "stretcher-01": (4, 0),  # MAINTENANCE
        "saw-01": (0, 0),
        "ageing-01": (0, 0),
    },
    "AGEING_OVEN_DEVIATION": {
        # Ageing oven temp out of band — T6 temper quality suspect on in-flight batch.
        "furnace-01": (2, 0),
        "press-01": (2, 0),
        "quench-01": (2, 0),
        "cooling-01": (2, 0),
        "stretcher-01": (2, 0),
        "saw-01": (2, 0),
        "ageing-01": (3, 711),  # AGE_TEMP_DEVIATION
    },
    "EMERGENCY_PRESS_TRIP": {
        # Press emergency stop — entire line down.
        "furnace-01": (0, 0),
        "press-01": (3, 219),  # PRESS_EMERGENCY_TRIP
        "quench-01": (0, 0),
        "cooling-01": (0, 0),
        "stretcher-01": (0, 0),
        "saw-01": (0, 0),
        "ageing-01": (0, 0),
    },
}

SCENARIO_MESSAGES: dict[str, str] = {
    "NORMAL": "All systems nominal. Extrusion + finishing on target. No action required.",
    "QUALITY_HOLD_QUENCH": "Quench flow below spec with rising exit temperature — P2 quality hold on in-box profiles. Automotive Customer B order at risk.",
    "PRESS_BOTTLENECK": "Extrusion press overload — downstream idle. Profile throughput halted at press.",
    "STRETCHER_BACKLOG": "Stretcher offline (maintenance). Cooling table accumulating WIP; saw + ageing starving.",
    "AGEING_OVEN_DEVIATION": "Ageing oven temperature out of T6 window — in-flight batch quality suspect. MNC Customer A order may be held for retest.",
    "EMERGENCY_PRESS_TRIP": "PRESS EMERGENCY TRIP — full line shutdown. All three customer orders at risk. Invoke BCP.",
}

SCENARIO_HEALTH: dict[str, str] = {
    "NORMAL": "GREEN",
    "QUALITY_HOLD_QUENCH": "AMBER",
    "PRESS_BOTTLENECK": "AMBER",
    "STRETCHER_BACKLOG": "AMBER",
    "AGEING_OVEN_DEVIATION": "AMBER",
    "EMERGENCY_PRESS_TRIP": "CRITICAL",
}

AUTO_EXPIRE_SECONDS = 600  # 10 minutes


def set_scenario(name: str) -> None:
    """Set the simulator to a named scenario.

    Non-normal demo scenarios auto-reset to ``NORMAL`` after AUTO_EXPIRE_SECONDS.
    ``NORMAL`` is an explicit, stable all-running state rather than a return to
    background cycling.
    """
    if name not in SCENARIO_STATES:
        raise ValueError(f"Unknown scenario: {name!r}. Valid: {list(SCENARIO_STATES)}")
    with _lock:
        global _scenario, _expires_at
        _scenario = name
        _expires_at = time.time() + AUTO_EXPIRE_SECONDS if name != "NORMAL" else 0.0


def get_scenario() -> str:
    """Return the current active scenario name, resetting expired locks."""
    with _lock:
        global _scenario, _expires_at
        if _expires_at and time.time() > _expires_at:
            _scenario = "NORMAL"
            _expires_at = 0.0
        return _scenario


def get_override(asset_id: str) -> tuple[int, int] | None:
    """Return the active scenario state tuple for a given asset."""
    scenario = get_scenario()
    return SCENARIO_STATES[scenario].get(asset_id)


def status() -> dict:
    """Return full status dict for the scenario API response."""
    scenario = get_scenario()
    with _lock:
        remaining = max(0.0, _expires_at - time.time()) if _expires_at else 0.0
    return {
        "scenario": scenario,
        "health": SCENARIO_HEALTH[scenario],
        "message": SCENARIO_MESSAGES[scenario],
        "auto_resets_in_seconds": int(remaining) if remaining else None,
        "valid_scenarios": list(SCENARIO_STATES.keys()),
    }
