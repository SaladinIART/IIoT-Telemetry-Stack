"""POST /api/v1/demo/scenario/{name} — Trigger a named demo scenario.

Proxies the request to the modbus_sim scenario API (port 5001).
Used by the DemoControlPanel in the frontend to trigger scenario states
during live presentations without needing direct access to the simulator.
"""

from __future__ import annotations

import os
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path

from services.api.dependencies import require_api_key

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

_SIM_BASE = os.getenv("MODBUS_SIM_API", "http://modbus-sim:5001")

_VALID_SCENARIOS = {
    "NORMAL",
    "QUALITY_HOLD_QUENCH",
    "PRESS_BOTTLENECK",
    "STRETCHER_BACKLOG",
    "AGEING_OVEN_DEVIATION",
    "EMERGENCY_PRESS_TRIP",
}


@router.post("/scenario/{name}", dependencies=[Depends(require_api_key)])
def set_demo_scenario(
    name: Annotated[str, Path(description="Scenario name from aluminium-profile-line-1 catalog")],
) -> dict:
    name_upper = name.upper()
    if name_upper not in _VALID_SCENARIOS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scenario {name!r}. Valid options: {sorted(_VALID_SCENARIOS)}",
        )
    try:
        resp = httpx.post(
            f"{_SIM_BASE}/scenario",
            json={"scenario": name_upper},
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach simulator scenario API: {exc}",
        ) from exc


@router.get("/scenario", dependencies=[Depends(require_api_key)])
def get_demo_scenario() -> dict:
    """Return the current active scenario from the simulator."""
    try:
        resp = httpx.get(f"{_SIM_BASE}/scenario", timeout=3.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
