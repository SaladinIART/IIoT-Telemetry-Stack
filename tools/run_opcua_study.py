"""Retain actual separate-process experiments; never fabricate measurement data."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import socket
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {"normal": 4, "steady": 12, "frozen": 9, "bad": 4, "uncertain": 4, "process-fault": 4}


async def experiment(output, scenario, duration):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    endpoint = f"opc.tcp://127.0.0.1:{port}/nexus/"
    evidence = output / f"{scenario}.jsonl"
    with (output / f"{scenario}-server.log").open("x", encoding="utf-8") as stderr:
        server = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "iiot_stack.opcua_server",
            "--endpoint",
            endpoint,
            "--scenario",
            scenario,
            "--fault-after",
            "2",
            stdout=asyncio.subprocess.PIPE,
            stderr=stderr,
            cwd=ROOT,
        )
        try:
            ready = await asyncio.wait_for(server.stdout.readline(), timeout=15)
            if b"server ready" not in ready:
                raise RuntimeError(f"{scenario}: server did not become ready")
            stderr.write(ready.decode())
            client = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "iiot_stack.opcua_client",
                "--endpoint",
                endpoint,
                "--duration",
                str(duration),
                "--output",
                str(evidence),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=ROOT,
            )
            client_output, _ = await asyncio.wait_for(client.communicate(), duration + 15)
            (output / f"{scenario}-client.log").write_bytes(client_output)
            if client.returncode:
                raise RuntimeError(f"{scenario}: client exit={client.returncode}")
        finally:
            if server.returncode is None:
                server.terminate()
            await server.wait()
    rows = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines()]
    payloads = [r["payload"] for r in rows if r["kind"] == "telemetry"]
    counts = Counter(r["kind"] for r in rows)
    result = {
        "duration_seconds": duration,
        "record_counts": dict(counts),
        "payload_count": len(payloads),
    }
    assert counts["connected"] and payloads, f"{scenario}: no actual accepted data"
    if scenario == "steady":
        temps = [p for p in payloads if p["signal"] == "billet_temp_c"]
        assert len({p["source_ts"] for p in temps}) == 1 and not counts["acquisition_stale"]
        result["steady_temperature_source_timestamp_unchanged"] = True
    if scenario == "frozen":
        assert counts["acquisition_stale"]
        first_stale = next(i for i, row in enumerate(rows) if row["kind"] == "acquisition_stale")
        assert not any(row["kind"] == "telemetry" for row in rows[first_stale:])
    if scenario in {"bad", "uncertain"}:
        assert any(r["kind"] == "rejected" and "non_good_status" in r["reason"] for r in rows)
    if scenario == "process-fault":
        assert any(p["state"] == "FAULTED" and p["quality"] == "good" for p in payloads)
    result["acceptance"] = "PASS"
    print(f"{scenario}: PASS ({len(payloads)} candidate payloads)", flush=True)
    return result


async def run(output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "started_at": datetime.now(UTC).isoformat(),
        "evidence_label": "Simulated",
        "description": "Real local OPC UA traffic between separate Python processes; fictional equipment inputs",
        "python": platform.python_version(),
        "platform": platform.system(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("asyncua", "paho-mqtt", "jsonschema")
        },
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted((ROOT / "src/iiot_stack").glob("opcua_*.py"))
        },
        "scenarios": {},
        "mqtt_database_dashboard": "NOT EXERCISED by this separate-process runner",
    }
    manifest_path = output / "manifest.json"
    try:
        for name, duration in SCENARIOS.items():
            manifest["scenarios"][name] = await experiment(output, name, duration)
    finally:
        manifest["finished_at"] = datetime.now(UTC).isoformat()
        manifest["artifacts_sha256"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.iterdir())
            if path.is_file() and path != manifest_path
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New directory; existing evidence is never overwritten",
    )
    asyncio.run(run(parser.parse_args().output))
