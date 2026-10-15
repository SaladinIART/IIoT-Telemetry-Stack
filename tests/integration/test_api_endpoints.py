"""
Integration tests for the NEXUS REST API.

Prerequisites:
  - TimescaleDB running with migrations applied (docker compose up timescaledb)
  - Environment variables set (PGHOST, PGUSER, PGPASSWORD, PGDATABASE, API_KEY)

Run with:
  pytest tests/integration/test_api_endpoints.py -v
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Skip entire module when DB is not reachable (CI without compose)
pytest.importorskip("psycopg")

API_KEY = os.getenv("API_KEY", "nexus-dev-key-change-me")
AUTH = {"X-API-Key": API_KEY}


@pytest.fixture(scope="module")
def client():
    from services.api.main import app

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── health ────────────────────────────────────────────────────────────────────


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── auth ──────────────────────────────────────────────────────────────────────


def test_missing_api_key_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/assets")
    assert resp.status_code == 401


def test_wrong_api_key_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/assets", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


# ── assets ────────────────────────────────────────────────────────────────────


def test_list_assets_returns_list(client: TestClient) -> None:
    resp = client.get("/api/v1/assets", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


def test_get_unknown_asset_404(client: TestClient) -> None:
    resp = client.get("/api/v1/assets/nonexistent-asset-xyz", headers=AUTH)
    assert resp.status_code == 404


# ── alerts ────────────────────────────────────────────────────────────────────


def test_list_alerts_returns_list(client: TestClient) -> None:
    resp = client.get("/api/v1/alerts", headers=AUTH)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_alerts_state_filter(client: TestClient) -> None:
    resp = client.get("/api/v1/alerts?state=OPEN", headers=AUTH)
    assert resp.status_code == 200
    for alert in resp.json():
        assert alert["state"] == "OPEN"


def test_acknowledge_nonexistent_alert_404(client: TestClient) -> None:
    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = client.post(f"/api/v1/alerts/{fake_id}/acknowledge", headers=AUTH, json={})
    assert resp.status_code == 404


# ── kpis ──────────────────────────────────────────────────────────────────────


def test_kpis_returns_list(client: TestClient) -> None:
    resp = client.get("/api/v1/kpis", headers=AUTH)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── sites ─────────────────────────────────────────────────────────────────────


def test_list_sites(client: TestClient) -> None:
    resp = client.get("/api/v1/sites", headers=AUTH)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # demo-site is seeded in migration 003
    site_ids = [s["site_id"] for s in body]
    assert "demo-site" in site_ids


# ── docs ──────────────────────────────────────────────────────────────────────


def test_swagger_ui_reachable(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()
