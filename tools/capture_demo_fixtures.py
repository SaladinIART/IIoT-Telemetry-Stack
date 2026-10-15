"""Capture real NEXUS API output for every demo scenario.

Run against a live stack (``docker compose up --build -d``). For each scenario
the script switches the simulator, waits for the pipeline to settle, then
records the JSON the browser demo will replay. Nothing is fabricated: output
is whatever the API returned, plus a manifest with the capture time and git SHA.

    python tools/capture_demo_fixtures.py --base-url http://localhost:8080
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SCENARIOS = [
    "NORMAL",
    "QUALITY_HOLD_QUENCH",
    "PRESS_BOTTLENECK",
    "STRETCHER_BACKLOG",
    "AGEING_OVEN_DEVIATION",
    "EMERGENCY_PRESS_TRIP",
]
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "frontend" / "static" / "demo-fixtures"
DEFAULT_API_KEY = "nexus-dev-key-change-me"  # public demo placeholder, see .env.example


class Api:
    def __init__(self, base_url: str, api_key: str, timeout: float = 15.0) -> None:
        self.base = base_url.rstrip("/") + "/api/v1"
        self.key = api_key
        self.timeout = timeout

    def request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"X-API-Key": self.key, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode())

    def get(self, path: str):
        return self.request("GET", path)

    def post(self, path: str, body: dict | None = None):
        return self.request("POST", path, body or {})


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def capture_scenario(api: Api, scenario: str, out: Path, settle: float, tel_limit: int) -> dict:
    api.post(f"/demo/scenario/{scenario}")
    time.sleep(settle)
    state = api.get("/demo/scenario")
    if state.get("scenario") != scenario:
        raise RuntimeError(f"simulator reports {state.get('scenario')!r}, expected {scenario!r}")
    assets = api.get("/assets")
    folder = out / scenario
    write_json(folder / "scenario.json", state)
    write_json(folder / "dashboard.json", api.get("/dashboard"))
    write_json(folder / "assets.json", assets)
    write_json(folder / "alerts.json", api.get("/alerts?limit=200"))
    write_json(folder / "kpis.json", api.get("/kpis?window=8"))
    for asset in assets:
        points = api.get(f"/assets/{asset['asset']}/telemetry?limit={tel_limit}")
        write_json(folder / "telemetry" / f"{asset['asset']}.json", points)
    return {"scenario": scenario, "assets": len(assets), "health": state.get("health")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--api-key", default=DEFAULT_API_KEY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--settle-seconds", type=float, default=25.0)
    ap.add_argument("--telemetry-limit", type=int, default=300)
    args = ap.parse_args(argv)

    api = Api(args.base_url, args.api_key)
    try:
        summaries = [
            capture_scenario(api, s, args.output, args.settle_seconds, args.telemetry_limit)
            for s in SCENARIOS
        ]
        write_json(args.output / "sites.json", api.get("/sites"))
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:  # always leave the simulator in the stable all-running state
            api.post("/demo/scenario/NORMAL")
        except Exception:  # noqa: BLE001
            pass

    write_json(
        args.output / "manifest.json",
        {
            "source": "captured",
            "captured_at": datetime.now(UTC).isoformat(),
            "git_sha": git_sha(),
            "base_url": args.base_url,
            "settle_seconds": args.settle_seconds,
            "scenarios": summaries,
        },
    )
    print(f"captured {len(summaries)} scenarios -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
