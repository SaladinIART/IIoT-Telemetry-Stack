# Checkpoint 10 - Final Polish and Handoff

Date: 2026-04-25

## Objective

Close the recovery plan with a practical handoff:

- what is fully working
- what is demo-ready but still a little rough
- what remains optional polish
- how to run the live demo step by step

## Current Status

### Fully working

- Aluminium profile line simulator with 7 stations:
  - `furnace-01`
  - `press-01`
  - `quench-01`
  - `cooling-01`
  - `stretcher-01`
  - `saw-01`
  - `ageing-01`
- Demo scenario API with all 6 scenarios:
  - `NORMAL`
  - `QUALITY_HOLD_QUENCH`
  - `PRESS_BOTTLENECK`
  - `STRETCHER_BACKLOG`
  - `AGEING_OVEN_DEVIATION`
  - `EMERGENCY_PRESS_TRIP`
- Clean DB bootstrap with the aluminium migration path
- SQL decision surface:
  - `v_aluminium_line_current_state`
  - `v_aluminium_decision_board`
  - `v_aluminium_quality_risk`
  - `v_aluminium_business_risk`
- FastAPI runtime serving live aluminium dashboard data
- Svelte executive dashboard rendering and scenario controls
- Grafana provisioning for the aluminium decision board
- End-to-end scenario proof across simulator, API, DB, Svelte, and Grafana
- Top-level docs and runbooks updated to the aluminium demo story

### Demo-ready but rough

- Grafana throughput panel is serviceable but still visually sparse in screenshots
- Direct deep-link to `http://localhost:8080/dashboard` still returns `404`
  - use `http://localhost:8080/` and navigate to **Executive View**
- Returning to `NORMAL` after a heavy scenario can require a slightly longer settle window
  - use about `10–12 seconds` before narrating the fully recovered state

### Optional polish

- Make `v_aluminium_quality_risk` more scenario-local so it suppresses historical alert noise
- Make `v_aluminium_business_risk` follow the active scenario more tightly
- Refresh any screenshot assets under `docs/screenshots/` so they match the aluminium UI
- Add deeper API examples for demo-specific endpoints if external reviewers will read the docs closely

## Live Environment Snapshot

At checkpoint close, the local stack is up:

- API: `http://localhost:8080`
- Grafana: `http://localhost:3000`
- Modbus simulator API: `http://localhost:5001`
- TimescaleDB: `localhost:5432`
- Mosquitto: `localhost:1883`

## Operator Run Sequence

### 1. Start the stack

```bash
docker compose up --build -d
```

### 2. Open the two live demo surfaces

- Grafana: `http://localhost:3000`
  - user: `admin`
  - password: `change_me_now`
- Web app: `http://localhost:8080/`
  - then open **Executive View** from the sidebar

### 3. Set the board to a known good baseline

```bash
curl -s -X POST \
  -H "X-API-Key: nexus-dev-key-change-me" \
  http://localhost:8080/api/v1/demo/scenario/NORMAL
```

Wait about `10 seconds`.

### 4. Narrate baseline state

Start with **Grafana first**:

- line health green
- no urgent decision rows
- no active quality hold story

Then use **Svelte second**:

- executive banner green
- all 7 stations healthy
- management actions quiet / nominal

### 5. Trigger the flagship scenario

```bash
curl -s -X POST \
  -H "X-API-Key: nexus-dev-key-change-me" \
  http://localhost:8080/api/v1/demo/scenario/QUALITY_HOLD_QUENCH
```

Wait about `10 seconds`.

### 6. Narrate the incident in the strongest order

Use **Grafana first**:

1. `Line Health` changes from green to amber/red-context on the board
2. `Decision Board — Recommended Actions`
   - Quality places `BATCH-AL-241024-Q3` on P2 hold
   - Maintenance dispatches to `quench-01`
   - Shift Supervisor notifies Automotive Customer B
3. `Quality Risk — Batches in the Box`
   - show affected batch/order/customer
4. `Business Risk — Value at Risk by Customer`
   - show customer exposure
5. `Station Telemetry Trend — quench-01`
   - flow drops
   - exit temperature rises

Then use **Svelte second**:

1. banner turns amber
2. floor map highlights the line impact in a management-friendly way
3. action cards show the same decision story in executive language

## Recommended Demo Script

Short version:

1. Open Grafana and Svelte side by side
2. Show green `NORMAL`
3. Trigger `QUALITY_HOLD_QUENCH`
4. Explain:
   - evidence
   - hold decision
   - customer exposure
   - owner-specific actions
5. Reset to `NORMAL`

## Residual Risks

### P1

- None blocking the live aluminium demo flow

### P2

- Quality/business risk panels are still a little broader than the active scenario because open alert history can bleed into those views

### P3

- Throughput panel presentation could be improved
- direct `/dashboard` route support would be cleaner for external sharing

## Result

The aluminium demo is now runnable, coherent, and presentation-ready.

The safest recommendation is:

- use Grafana as the primary storytelling surface
- use Svelte as the executive/secondary view
- anchor the live demo on `QUALITY_HOLD_QUENCH`

Checkpoint 10 is complete.
