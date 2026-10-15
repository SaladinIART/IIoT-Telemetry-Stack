"""Demo fixture tooling: shapes must match the real API schemas."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from services.api.schemas.alert import AlertOut
from services.api.schemas.asset import AssetSummary
from services.api.schemas.dashboard import DashboardResponse
from services.api.schemas.kpi import KpiSummary
from services.api.schemas.telemetry import TelemetryPoint
from tools import capture_demo_fixtures as capture
from tools import make_placeholder_demo_fixtures as placeholder


@pytest.fixture(scope="module")
def placeholder_dir(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("fixtures")
    assert placeholder.main(["--output", str(out)]) == 0
    return out


def test_placeholder_manifest_is_marked_not_captured(placeholder_dir: Path):
    manifest = json.loads((placeholder_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["source"] == "placeholder"


@pytest.mark.parametrize("scenario", capture.SCENARIOS)
def test_placeholder_payloads_match_api_schemas(placeholder_dir: Path, scenario: str):
    folder = placeholder_dir / scenario
    dash = DashboardResponse.model_validate_json((folder / "dashboard.json").read_text("utf-8"))
    assert dash.scenario == scenario
    for name, model in (
        ("assets.json", AssetSummary),
        ("alerts.json", AlertOut),
        ("kpis.json", KpiSummary),
    ):
        for row in json.loads((folder / name).read_text("utf-8")):
            model.model_validate(row)
    files = list((folder / "telemetry").glob("*.json"))
    assert len(files) == 7
    for row in json.loads(files[0].read_text("utf-8")):
        TelemetryPoint.model_validate(row)


def test_faulted_scenario_has_alert_and_non_green_health(placeholder_dir: Path):
    dash = json.loads(
        (placeholder_dir / "QUALITY_HOLD_QUENCH" / "dashboard.json").read_text("utf-8")
    )
    alerts = json.loads(
        (placeholder_dir / "QUALITY_HOLD_QUENCH" / "alerts.json").read_text("utf-8")
    )
    assert dash["health"] == "AMBER"
    assert [a["asset"] for a in alerts] == ["quench-01"]


class _StubApi(BaseHTTPRequestHandler):
    current = "NORMAL"

    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.headers.get("X-API-Key") != "k":
            self.send_error(401)
            return
        type(self).current = self.path.rsplit("/", 1)[-1]
        self._send({"scenario": type(self).current})

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path.endswith("/demo/scenario"):
            self._send({"scenario": type(self).current, "health": "GREEN"})
        elif path.endswith("/assets"):
            self._send([{"asset": "press-01"}])
        else:
            self._send([])

    def log_message(self, *args):  # silence
        pass


def test_capture_writes_every_scenario_and_manifest(tmp_path: Path):
    server = HTTPServer(("127.0.0.1", 0), _StubApi)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        rc = capture.main(
            [
                "--base-url",
                f"http://127.0.0.1:{server.server_port}",
                "--api-key",
                "k",
                "--output",
                str(tmp_path),
                "--settle-seconds",
                "0",
            ]
        )
    finally:
        server.shutdown()
    assert rc == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text("utf-8"))
    assert manifest["source"] == "captured"
    assert [s["scenario"] for s in manifest["scenarios"]] == capture.SCENARIOS
    assert (tmp_path / "PRESS_BOTTLENECK" / "telemetry" / "press-01.json").exists()
