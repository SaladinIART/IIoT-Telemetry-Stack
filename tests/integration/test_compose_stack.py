from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]


def docker_available() -> bool:
    result = subprocess.run(
        ["docker", "info"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.integration
def test_compose_stack_end_to_end() -> None:
    if not docker_available():
        pytest.skip("Docker daemon is not reachable in this environment")

    up = subprocess.run(
        ["docker", "compose", "up", "--build", "-d"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert up.returncode == 0, up.stderr
    try:
        deadline = time.time() + 90
        healthy = False
        while time.time() < deadline:
            try:
                response = requests.get("http://localhost:3000/api/health", timeout=2)
                if response.ok:
                    healthy = True
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        assert healthy, "Grafana did not become healthy"

        query = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "timescaledb",
                "psql",
                "-U",
                os.getenv("POSTGRES_USER", "iiot"),
                "-d",
                os.getenv("POSTGRES_DB", "iiot"),
                "-c",
                "SELECT COUNT(*) FROM telemetry;",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert query.returncode == 0, query.stderr
        assert "count" in query.stdout.lower()
    finally:
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
