# NEXUS — Build Progress

Live checklist. Updated as each task is completed.

---

## Phase 0 — Foundation Stabilization

- [x] Rename project to `nexus-iiot-platform`, update `pyproject.toml`
- [x] Add Phase 2/3 dependencies: `fastapi`, `uvicorn`, `scikit-learn`, `numpy`, `httpx`, `psycopg-pool`, `ruff`
- [x] Expand `.env.example` with API + alert engine variables (documented)
- [x] Expand `README.md` — architecture diagram, tech stack table, quick start, docs links
- [x] Write `docs/architecture.md` — full system diagram and data flow narrative
- [x] Write `docs/adr/001` — TimescaleDB over InfluxDB
- [x] Write `docs/adr/002` — FastAPI + Svelte frontend
- [x] Write `docs/adr/003` — 3-layer alert architecture
- [x] Write `docs/adr/004` — ISA-95 MQTT topic hierarchy
- [x] Create stub migration files `002–004` (ready for Phase 1)
- [x] Create `PROGRESS.md`

---

## Phase 1 — Database Extensions

- [x] `db/migrations/002_alerts.sql` — `alerts` table + `alert_rules` table (with seeded default rules)
- [x] `db/migrations/003_site_config.sql` — `sites` table + `site_assets` view
- [x] `db/migrations/004_api_views.sql` — `v_asset_current_state`, `v_recent_alerts`, `v_kpi_summary`
- [x] `contracts/alert_payload.schema.json` — JSON schema for alert MQTT events

---

## Phase 2 — Alert Detector + Router

- [x] `services/alerting/rules.py` — `RuleLoader` (DB → alert rules, refresh every 60s)
- [x] `services/alerting/models/anomaly.py` — `AnomalyScorer` (IsolationForest wrapper)
- [x] `services/alerting/detector.py` — Layer 1: threshold check
- [x] `services/alerting/detector.py` — Layer 2: statistical baseline (z-score)
- [x] `services/alerting/detector.py` — Layer 3: ML anomaly (IsolationForest)
- [x] `services/alerting/router.py` — dedup + DB write + MQTT publish + webhook
- [x] `services/alerting/Dockerfile` + add service to `docker-compose.yml`
- [x] `tests/unit/test_detector.py` + `tests/unit/test_router.py`

**Verification:** inject spike → alert row in `alerts` table within 2 poll cycles

---

## Phase 3 — REST API Service

- [x] `services/api/dependencies.py` — DB pool, API key auth, `APISettings`
- [x] `services/api/schemas/` — 4 Pydantic model files (asset, telemetry, alert, kpi)
- [x] `services/api/routers/assets.py`
- [x] `services/api/routers/telemetry.py`
- [x] `services/api/routers/alerts.py` (GET + POST acknowledge)
- [x] `services/api/routers/kpis.py` + `sites.py`
- [x] `services/api/routers/stream.py` — SSE endpoints
- [x] `services/api/main.py` + `Dockerfile` + add service to `docker-compose.yml`
- [x] `tests/integration/test_api_endpoints.py`

**Verification:** `GET /api/v1/assets` returns 4 assets · `GET /docs` shows Swagger UI · SSE stream opens

---

## Phase 4 — Frontend (Svelte 5)

- [x] `frontend/` project setup — `package.json`, `vite.config.ts`, `svelte.config.js`
- [x] `frontend/src/lib/` — `api.ts`, `sse.ts`, `stores.ts`, `types.ts`
- [x] Components — `AssetCard`, `SignalChart`, `AlertBadge`, `KpiGauge`, `StatusPill`, `SiteSelector`
- [x] `+layout.svelte` — sidebar nav + top bar
- [x] `/` floor overview page (live asset grid via SSE)
- [x] `/assets` and `/assets/[id]` pages
- [x] `/alerts` page (inbox + acknowledge)
- [x] `/kpis` and `/admin` pages

**Verification:** `http://localhost:8000` loads floor overview · 4 asset cards update live · alert acknowledge works

---

## Phase 5 — CI/CD Pipeline

- [x] `.github/workflows/ci.yml` — ruff lint + pytest unit + Svelte build
- [x] `.github/workflows/integration.yml` — compose smoke test on PRs to main
- [x] `.github/workflows/release.yml` — build + push GHCR images on `v*` tags

**Verification:** GitHub Actions shows green on all 3 workflows

---

## Phase 6 — Tier 2 Multi-Site

> **Removed 2026-10-15 (portfolio CP-3):** The multi-site overlay (`docker-compose.multi.yml`, EMQX) and runbook 04 was never exercised in CI and has been deleted so the repository only claims what is verified. Recover from git history before the CP-3 commit if needed.

- [x] `docker-compose.multi.yml` — `collector_site_b` + `modbus_sim_b` + EMQX + seed
- [x] `infra/grafana/provisioning/dashboards/json/production_kpis.json` — multi-site variable panel
- [x] `docs/runbooks/04-scaling-to-tier2.md`

**Verification:** `SELECT DISTINCT site FROM telemetry` returns 2 values

---

## Phase 7 — Documentation + Runbooks

- [x] `docs/runbooks/01-quickstart.md` — zero to running stack in 15 min
- [x] `docs/runbooks/02-adding-new-asset.md`
- [x] `docs/runbooks/03-alert-tuning.md`
- [x] `docs/api-reference.md` — all endpoints with examples
- [x] `docs/data-model.md` — all tables and views explained
- [x] `README.md` — screenshots section + data-model link added

**Verification:** colleague follows quickstart with zero support in < 15 minutes

---

## Phase 8 — Kubernetes Helm Charts *(optional, high-impact)*

> **Removed 2026-10-15 (portfolio CP-3):** The Helm chart (`helm/nexus/`) and runbook 05 — never tested on a cluster — was never exercised in CI and has been deleted so the repository only claims what is verified. Recover from git history before the CP-3 commit if needed.

- [x] `helm/nexus/Chart.yaml` + `values.yaml`
- [x] `helm/nexus/templates/` — `_helpers.tpl`, `secrets`, `emqx`, `modbus-sim`, `collector`, `ingestor`, `alerting`, `api`, `ingress`, `hpa`
- [x] `docs/runbooks/05-scaling-to-tier3.md`
- [ ] Test on local Minikube  *(run manually after pushing images)*

**Verification:** `helm install nexus ./helm/nexus` — all pods Running

---

## End-to-End Verification Checklist

Run this after Phase 4 is complete to confirm the full system works:

```bash
git clone ... && cp .env.example .env && docker compose up --build
```

- [ ] `http://localhost:8000` — Svelte floor overview loads, 4 asset cards update live
- [ ] `http://localhost:3000` — Grafana operator dashboard shows telemetry
- [ ] Inject spike into simulator → alert appears in `/alerts` within 10s
- [ ] Acknowledge alert → state changes to ACKED
- [ ] `curl -H "X-API-Key: nexus-dev-key-change-me" http://localhost:8000/api/v1/assets` returns JSON
- [ ] `pytest tests/` — all tests pass
- [ ] Push to GitHub → CI workflow green
