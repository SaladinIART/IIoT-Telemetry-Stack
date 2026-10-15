"""Verify an already-running, isolated OPC UA Compose stack; no teardown here."""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.opcua.yml"]


def compose(*args):
    return subprocess.run(
        [*COMPOSE, *args], check=True, text=True, capture_output=True, timeout=20
    ).stdout


def request_json(url, *, data=None, headers=None):
    request = Request(url, data=json.dumps(data).encode() if data else None, headers=headers or {})
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def verify(output):
    output.mkdir(parents=True, exist_ok=False)
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "FAIL",
        "equipment": "Simulated",
        "checks": {},
    }
    try:
        deadline = time.monotonic() + 150
        last_error = None
        while time.monotonic() < deadline:
            try:
                raw = compose(
                    "exec",
                    "-T",
                    "collector",
                    "python",
                    "-c",
                    "from pathlib import Path; print(''.join(p.read_text() for p in sorted(Path('/evidence').glob('*.jsonl'))))",
                )
                rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
                acked = {r["seq"] for r in rows if r["kind"] == "mqtt_published"}
                payload = next(
                    r["payload"]
                    for r in rows
                    if r["kind"] == "telemetry"
                    and r["payload"]["signal"] == "billet_temp_c"
                    and r["payload"]["seq"] in acked
                )
                sql = (
                    "SELECT row_to_json(t) FROM (SELECT asset,signal,value,quality,state,fault_code,seq,"
                    "round(extract(epoch from source_ts)*1000)::bigint AS source_ts,"
                    "round(extract(epoch from ts)*1000)::bigint AS ts FROM telemetry "
                    f"WHERE asset='furnace-01' AND signal='billet_temp_c' AND seq={int(payload['seq'])} "
                    f"AND ts=to_timestamp({int(payload['ts'])}/1000.0) LIMIT 1) t"
                )
                row = json.loads(
                    compose(
                        "exec",
                        "-T",
                        "timescaledb",
                        "psql",
                        "-U",
                        "iiot",
                        "-d",
                        "iiot",
                        "-At",
                        "-c",
                        sql,
                    )
                )
                assert all(row[key] == payload[key] for key in row), (row, payload)
                assert request_json("http://127.0.0.1:8080/health")["status"] == "ok"
                api_asset = request_json(
                    "http://127.0.0.1:8080/api/v1/assets/furnace-01",
                    headers={"X-API-Key": os.getenv("API_KEY", "nexus-dev-key-change-me")},
                )
                assert api_asset["asset"] == "furnace-01"
                basic = base64.b64encode(
                    f"{os.getenv('GRAFANA_ADMIN_USER', 'admin')}:{os.getenv('GRAFANA_ADMIN_PASSWORD', 'change_me_now')}".encode()
                ).decode()
                headers = {"Authorization": f"Basic {basic}", "Content-Type": "application/json"}
                dashboard = request_json(
                    "http://127.0.0.1:3000/api/dashboards/uid/nexus-opcua", headers=headers
                )
                assert dashboard["dashboard"]["uid"] == "nexus-opcua"
                grafana = request_json(
                    "http://127.0.0.1:3000/api/ds/query",
                    headers=headers,
                    data={
                        "from": str(payload["ts"] - 60000),
                        "to": str(payload["ts"] + 60000),
                        "queries": [
                            {
                                "refId": "A",
                                "datasource": {"uid": "iiot-timescaledb", "type": "postgres"},
                                "format": "table",
                                "rawSql": f"SELECT value FROM telemetry WHERE asset='furnace-01' AND signal='billet_temp_c' AND seq={int(payload['seq'])} AND ts=to_timestamp({int(payload['ts'])}/1000.0) LIMIT 1",
                            }
                        ],
                    },
                )
                assert (
                    grafana["results"]["A"]["frames"][0]["data"]["values"][0][0] == payload["value"]
                )
                result.update(status="PASS", payload=payload, database_row=row, api_asset=api_asset)
                result["checks"] = {
                    "opcua_subscription": True,
                    "mqtt_puback": True,
                    "database_exact_row": True,
                    "api_asset": True,
                    "grafana_datasource_exact_value": True,
                    "grafana_dashboard_provisioned": True,
                }
                (output / "collector.jsonl").write_text(raw, encoding="utf-8")
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                time.sleep(2)
        if result["status"] != "PASS":
            result["last_error"] = last_error
            raise RuntimeError(f"Stack did not pass within deadline: {last_error}")
    finally:
        (output / "verification.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    print("PASS: actual OPC UA -> MQTT -> TimescaleDB -> API/Grafana data-source trace")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
