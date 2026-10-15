# NEXUS — System Architecture

## Overview

NEXUS is a self-contained IIoT monitoring platform. It collects sensor data from factory floor equipment via Modbus TCP, routes it through an MQTT broker, persists it in TimescaleDB, detects anomalies in real time, and exposes a REST/SSE API consumed by a Svelte web application and Grafana dashboards.

The implemented and CI-verified deployment is a single-host Docker Compose stack. The MQTT topics and database schema carry a `site` dimension from day one, so additional sites would not require schema changes.

---

## Full System Diagram

```
═══════════════════════════════════════════════════════════════════════════════
 OT LAYER  (Field Devices / Simulation)
═══════════════════════════════════════════════════════════════════════════════

  sim/modbus_sim/app.py
  │  Assets: furnace-01 · press-01 · quench-01 · cooling-01 · stretcher-01 · saw-01 · ageing-01
  │  Protocol: Modbus TCP :1502
  │  Signals: analog (float32), counter (int16), state, fault codes
  │  Pattern: scenario-based 90s state cycle with fault injection
  │
  └──── Modbus TCP ────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════════════
 COLLECTION LAYER
═══════════════════════════════════════════════════════════════════════════════

  services/collector/app.py
  │  - Polls each asset at COLLECT_INTERVAL_MS (default: 1000ms)
  │  - Decodes 16-bit int and 32-bit float registers (big-endian)
  │  - Applies scaling/offset transformations from register_map.json
  │  - State machine: RUNNING → IDLE → FAULTED → MAINTENANCE
  │  - Detects state transitions → emits typed event payloads
  │  - Quality: good / bad / stale based on asset state
  │  - Retry: exponential backoff 1s → 30s on Modbus failure
  │  - Publishes to MQTT QoS 1 (telemetry not retained, events retained)
  │
  │  MQTT topics:
  │    iiot/v1/telemetry/{site}/{line}/{asset}/{signal}
  │    iiot/v1/events/{site}/{line}/{asset}/{event_type}
  │    iiot/v1/alerts/{site}/{line}/{asset}/{alert_id}    ← written by alerting
  │
  └──── MQTT QoS 1 ────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════════════
 MESSAGE LAYER
═══════════════════════════════════════════════════════════════════════════════

  infra/mosquitto/    Eclipse Mosquitto :1883
  │  - ACL-based topic authorization (per-service credentials)
  │  - Clients: collector · ingestor · alerting
  │
  └─────────────────────────────────────┬──────────────────────────────────────
                                        │ fan-out to parallel subscribers
                         ┌──────────────┴──────────────┐
                         ▼                             ▼

═══════════════════════════════════════════════════════════════════════════════
 PROCESSING LAYER  (parallel MQTT subscribers)
═══════════════════════════════════════════════════════════════════════════════

  services/ingestor/app.py              services/alerting/
  │                                     │
  │  - JSON schema validation            │  detector.py
  │  - Extracts site/line/asset          │  ├─ Layer 1: Threshold rules
  │    from topic hierarchy              │  │   compare value vs alert_rules table
  │  - Batch buffer: flush on            │  ├─ Layer 2: Statistical baseline
  │    200 rows OR 1.0s timeout          │  │   rolling window (100 samples)
  │  - ON CONFLICT DO NOTHING            │  │   fire if |z-score| > threshold
  │    (idempotent inserts)              │  └─ Layer 3: ML anomaly
  │  - Writes: telemetry + events        │      IsolationForest, refit /500 samples
  │                                     │
  │                                     │  router.py
  │                                     │  - Deduplication window (5 min default)
  │                                     │  - Writes to alerts table
  │                                     │  - Publishes MQTT alert events
  │                                     │  - Webhook POST (Teams / Slack)
  │                                     │  - Auto-close when value normalises
  │                                     │
  └──── SQL INSERT ──────────────────────┴──── SQL INSERT ────────────────────

═══════════════════════════════════════════════════════════════════════════════
 STORAGE LAYER
═══════════════════════════════════════════════════════════════════════════════

  TimescaleDB (PostgreSQL 16)

  Hypertables:
  ┌─────────────────────────────────────────────────────────────┐
  │  telemetry    (ts, asset, signal, value, quality, seq_id)   │
  │  events       (ts, asset, event_type, state, fault_code)    │
  │  alerts       (id, asset, signal, type, severity, state,    │
  │                value, threshold, opened_at, acked_at,       │  ← Phase 1
  │                closed_at, rule_id)                          │
  └─────────────────────────────────────────────────────────────┘

  Reference tables:
  ┌─────────────────────────────────────────────────────────────┐
  │  asset_metadata   (asset_id, display_name, line, site, ...) │
  │  alert_rules      (asset, signal, warn/crit thresholds)     │  ← Phase 1
  │  sites            (site_id, display_name, timezone)         │  ← Phase 1
  └─────────────────────────────────────────────────────────────┘

  Pre-computed views:
  ┌─────────────────────────────────────────────────────────────┐
  │  telemetry_latest        most recent value per asset/signal │
  │  asset_status            current state + fault per asset    │
  │  production_kpis         OEE, throughput per asset          │
  │  v_asset_current_state   latest telemetry + open alerts     │  ← Phase 1
  │  v_recent_alerts         last 100 alerts with display names │  ← Phase 1
  │  v_kpi_summary           OEE + throughput per shift window  │  ← Phase 1
  └─────────────────────────────────────────────────────────────┘

  Compression: telemetry after 7 days · events after 14 days
  Retention:   telemetry 90 days       · events 180 days
  Indexes:     (asset, ts DESC) on both hypertables

  └──── SQL queries ──────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════════════
 API LAYER  (Phase 3)
═══════════════════════════════════════════════════════════════════════════════

  services/api/   FastAPI + Uvicorn :8000

  REST endpoints:
    GET  /api/v1/assets                      asset list + metadata
    GET  /api/v1/assets/{id}                 single asset with current state
    GET  /api/v1/assets/{id}/telemetry       time-range query (from/to/signal/limit)
    GET  /api/v1/assets/{id}/status          current state only
    GET  /api/v1/alerts                      active / recent alerts
    POST /api/v1/alerts/{id}/acknowledge     ack → state OPEN → ACKED
    GET  /api/v1/kpis                        OEE + production summary
    GET  /api/v1/sites                       multi-site list
    GET  /health                             liveness probe

  SSE (Server-Sent Events):
    GET  /api/v1/stream/telemetry    polls v_asset_current_state every 2s → push changes
    GET  /api/v1/stream/alerts       polls for new OPEN alerts → push immediately

  Auth:  X-API-Key request header
  Docs:  /docs  (Swagger UI, auto-generated from Pydantic schemas)
  Static: mounts frontend/dist/ at /  (serves compiled Svelte app)

  └──── HTTP + SSE ────────────────────────────────────────────────────────────

═══════════════════════════════════════════════════════════════════════════════
 FRONTEND LAYER  (Phase 4)
═══════════════════════════════════════════════════════════════════════════════

  frontend/  Svelte 5, compiled to vanilla JS, served by FastAPI

  Routes:
    /           App shell + navigation entry
    /dashboard  Executive dashboard — scenario banner, financial impact, actions, floor map
    /assets     Asset table with current state + last value
    /assets/[id]  Signal history chart (1h / 8h / 24h / 7d range picker)
    /alerts     Alert inbox — filter by state, acknowledge button
    /kpis       OEE gauges, production count bar chart, fault duration table
    /admin      Alert rule editor, API key display

  Key libraries:
    Chart.js    signal history charts
    EventSource SSE connection with exponential reconnect

═══════════════════════════════════════════════════════════════════════════════
 VISUALIZATION LAYER  (existing + enhanced)
═══════════════════════════════════════════════════════════════════════════════

  Grafana :3000
    overview.json             Aluminium Profile Decision Board
                              line health · decision board · quality risk · business risk
                              station process map · telemetry trends
    production_kpis.json      supporting KPI view

═══════════════════════════════════════════════════════════════════════════════
 INFRASTRUCTURE LAYER
═══════════════════════════════════════════════════════════════════════════════

  Deploy   docker-compose.yml             single host, one site (Modbus collector)
           docker-compose.opcua.yml       optional overlay: OPC UA collector instead

  CI/CD    .github/workflows/
             ci.yml            ruff lint + pytest unit + Svelte build  (every push)
             integration.yml   compose smoke test                       (PR to main)
             release.yml       build + push Docker images to GHCR       (v* tags)
```

---

## Data Flow (narrative)

1. **Modbus poll** — collector reads holding registers from each asset every 1000ms
2. **Payload build** — raw register values decoded, scaled, and wrapped in a versioned JSON payload with sequence ID, quality flag, and ISO 8601 timestamp
3. **Schema validation** — payload validated against `contracts/telemetry_payload.schema.json` before publish
4. **MQTT publish** — telemetry and state-change events published to topic hierarchy `iiot/v1/{type}/{site}/{line}/{asset}/{signal}`
5. **Ingestor** — subscribes, re-validates, batches rows, flushes to TimescaleDB on 200-row or 1s threshold
6. **Alert detector** — subscribes to the same telemetry topics in parallel:
   - Layer 1 checks value against configured thresholds from `alert_rules` table
   - Layer 2 computes z-score against a rolling per-sensor baseline
   - Layer 3 scores the value through a per-sensor IsolationForest model
7. **Alert router** — deduplicates, persists to `alerts` table, publishes alert event to MQTT, optionally POSTs to webhook
8. **API** — FastAPI queries TimescaleDB views. SSE endpoints poll every 2s and push delta to connected browsers
9. **Frontend** — Svelte stores update reactively from SSE stream, re-rendering only changed asset cards
10. **Grafana** — queries TimescaleDB directly via provisioned datasource for operator-level panels

---

## Multi-Site Readiness

The MQTT topic schema (`iiot/v1/{type}/{site}/{line}/{asset}/{signal}`) and the TimescaleDB tables both carry a `site` column from day one. A second site would mean another collector instance with a different `SITE` value; consumers already subscribe by wildcard and query by `site`.

Only the single-site Compose deployment is implemented and verified in CI. Multi-site overlays, a clustered broker and Kubernetes manifests are **not** part of this repository.

---

## Component Responsibilities (quick reference)

| Component | Owns | Does NOT own |
|-----------|------|-------------|
| `collector` | Modbus protocol, payload format, MQTT publish | Data storage, alerting |
| `ingestor` | Database writes, schema validation | Protocol, alerting logic |
| `alerting` | Detection logic, alert state machine, routing | Sensor data storage |
| `api` | HTTP interface, auth, SSE streaming | Business logic, direct MQTT |
| `frontend` | User interaction, real-time rendering | Data processing |
| `grafana` | Operator visualisation | User management, alerting |
| `timescaledb` | Persistence, time-series optimisation | All application logic |
| `mosquitto` | Message routing, ACL | Payload validation |
