# Checkpoint 7 - Grafana Decision-Board Validation

Date: 2026-04-24

## Objective

Validate Grafana as the primary live demo surface for the aluminium profile line, confirm provisioning works without manual edits, and verify that the flagship `QUALITY_HOLD_QUENCH` scenario produces a management-grade decision story.

## What Was Verified

### 1. Provisioning and datasource alignment

Grafana provisioning is healthy:

- container is up at `http://localhost:3000`
- datasource provisioning file uses explicit UID `iiot-timescaledb`
- dashboard JSON references the same datasource UID throughout
- dashboard provider is loading dashboards from `/etc/grafana/provisioning/dashboards/json`

Grafana API checks confirmed:

- `/api/health` returned healthy
- dashboard search returned:
  - `Aluminium Profile Decision Board`
  - `Production KPIs`
- dashboard UID `nexus-aluminium-decision-board` is provisioned and discoverable

### 2. Flagship scenario validated live

The live API was used to trigger:

- `QUALITY_HOLD_QUENCH`

After telemetry propagation, the SQL views backing Grafana reflected the incident correctly:

- `v_aluminium_line_current_state` showed:
  - `line_health = RED`
  - `line_scenario = QUALITY_HOLD_QUENCH`
  - `quench-01` faulted with `fault_code = 311`
  - quench evidence in live values:
    - `quench_flow_lpm` around `152`
    - `exit_temp_c` around `92.6`
- `v_aluminium_decision_board` returned the correct quench actions:
  - P2 quality hold for `BATCH-AL-241024-Q3`
  - maintenance dispatch to `quench-01`
  - shift-supervisor customer-notification action
  - operator diversion action
- `v_aluminium_quality_risk` returned live at-risk batch/order rows
- `v_aluminium_business_risk` returned customer-level value-at-risk rows including:
  - `MNC Customer A`
  - `Automotive Customer B`

### 3. Browser validation of Grafana

Grafana was logged into in the browser with the provisioned local admin account and the aluminium board was opened directly by UID.

Confirmed in the rendered dashboard:

- board title visible
- line-health stat visible
- open-alerts stat visible
- active-quality-holds stat visible
- decision-board table visible
- quality-risk table visible
- business-risk table visible
- station process map visible
- station telemetry trend visible
- flagship management action visible:
  - `Place BATCH-AL-241024-Q3 on P2 QUALITY HOLD`
- affected-customer context visible:
  - `Automotive Customer B`
- management escalation visible:
  - `Notify Automotive Customer B account manager`

The rendered board is the stronger demo surface relative to the Svelte dashboard because it concentrates:

- operational severity
- decision ownership
- batch/order/customer exposure
- evidence telemetry

in one screen.

## Fixes Applied During This Checkpoint

### Dashboard panel time override

The throughput panel title promised `last 8h`, but the board-wide time picker remained `Last 1 hour`.

`infra/grafana/provisioning/dashboards/json/overview.json` was updated so the throughput panel now uses:

- `"timeFrom": "8h"`

This makes the panel behavior match its own label.

### Throughput query simplification

The throughput panel query was simplified from a window-function shape to a direct hourly aggregate:

- from a `LAG(MAX(value))` pattern
- to `MAX(value) - MIN(value)` grouped by hour

This matches the direct SQL validation path and is easier to reason about.

## Residual Caveat

The throughput panel query returns valid hourly rows in PostgreSQL, and the panel now correctly advertises an `8h` override, but the chart still appears visually sparse in the headless Grafana screenshot.

This does **not** block the flagship demo because the core management story is already present and strong in:

- line health
- open alerts / holds
- decision board
- quality risk
- business risk
- telemetry trend

However, the throughput panel remains a follow-up polish item if a denser top-row chart is desired.

## Exit Criteria Result

- Grafana loads the aluminium dashboard from provisioning: yes
- datasource binds cleanly without manual editing: yes
- core panels render from live SQL-backed data: yes
- `QUALITY_HOLD_QUENCH` visibly shows:
  - P2 hold: yes
  - quench evidence: yes
  - affected order/customer exposure: yes
  - management action: yes

Checkpoint 7 is complete.
