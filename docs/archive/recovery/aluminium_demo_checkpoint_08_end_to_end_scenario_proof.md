# Checkpoint 8 - End-to-End Scenario Proof

Date: 2026-04-24

## Objective

Run the full aluminium demo stack as a rehearsal and prove that all 6 scenarios are triggerable and operationally distinct across:

- simulator
- API
- database views
- Svelte executive dashboard
- Grafana decision board

## Fixes Applied During This Checkpoint

### 1. Line-health severity alignment across Svelte and Grafana

Two scenario rollups in `v_aluminium_line_current_state` were too aggressive:

- `QUALITY_HOLD_QUENCH` was surfacing as `RED` in Grafana while the scenario API and executive dashboard correctly treated it as `AMBER`
- `PRESS_BOTTLENECK` was also surfacing as `RED` in Grafana while the scenario API and executive dashboard treated it as `AMBER`

`db/migrations/008_aluminium_decision_views.sql` was updated so:

- `RED` is reserved for the true line-down press emergency trip (`fault_code = 219`)
- other single-station aluminium demo faults now roll up to `AMBER`

The live DB view was reapplied after the migration edit.

## Validation Performed

### 1. Simulator, API, DB, and dashboard sweep

Each scenario was triggered through the live API, then allowed a settle window before verifying:

- `/api/v1/demo/scenario`
- `/api/v1/dashboard`
- `v_aluminium_line_current_state`
- `v_aluminium_decision_board`

Final settled results:

1. `NORMAL`
   - API scenario/health: `NORMAL / GREEN`
   - DB line scenario/health: `NORMAL / GREEN`
   - dashboard faulted machines: `0`
   - top action: continue planned production run

2. `QUALITY_HOLD_QUENCH`
   - API scenario/health: `QUALITY_HOLD_QUENCH / AMBER`
   - DB line scenario/health: `QUALITY_HOLD_QUENCH / AMBER`
   - dashboard faulted machines: `1`
   - top action: place `BATCH-AL-241024-Q3` on P2 quality hold

3. `PRESS_BOTTLENECK`
   - API scenario/health: `PRESS_BOTTLENECK / AMBER`
   - DB line scenario/health: `PRESS_BOTTLENECK / AMBER`
   - dashboard faulted machines: `1`
   - top action: inspect press overload / die back-end taper

4. `STRETCHER_BACKLOG`
   - API scenario/health: `STRETCHER_BACKLOG / AMBER`
   - DB line scenario/health: `STRETCHER_BACKLOG / AMBER`
   - dashboard faulted machines: `1`
   - top action: stretcher offline / confirm MTTR and backlog response

5. `AGEING_OVEN_DEVIATION`
   - API scenario/health: `AGEING_OVEN_DEVIATION / AMBER`
   - DB line scenario/health: `AGEING_OVEN_DEVIATION / AMBER`
   - dashboard faulted machines: `1`
   - top action: hold `BATCH-AL-241024-A2` for retest

6. `EMERGENCY_PRESS_TRIP`
   - API scenario/health: `EMERGENCY_PRESS_TRIP / CRITICAL`
   - DB line scenario/health: `EMERGENCY_PRESS_TRIP / RED`
   - dashboard faulted machines: `1`
   - top action: line down / invoke BCP

### 2. Svelte and Grafana UI proof

The live browser rehearsal exercised the scenario buttons in the Svelte executive dashboard and verified that the corresponding state became visible in both UI surfaces.

Validated for all 6 scenarios:

- Svelte scenario button triggers the scenario successfully
- Svelte banner updates to the expected scenario label / severity
- Grafana board reflects the scenario with the expected action/evidence text

Successful browser proof cases:

1. `NORMAL`
   - executive banner: `ALL SYSTEMS NORMAL`
   - Grafana action: normal production guidance visible

2. `QUALITY_HOLD_QUENCH`
   - executive banner: `QUENCH QUALITY HOLD`
   - Grafana: P2 quality-hold action and Automotive Customer B exposure visible

3. `PRESS_BOTTLENECK`
   - executive banner: `EXTRUSION PRESS OVERLOAD`
   - Grafana: press overload maintenance action visible

4. `STRETCHER_BACKLOG`
   - executive banner: `STRETCHER OFFLINE`
   - Grafana: stretcher backlog action visible

5. `AGEING_OVEN_DEVIATION`
   - executive banner: `AGEING OVEN OUT OF T6 BAND`
   - Grafana: batch hold and MNC Customer A exposure visible

6. `EMERGENCY_PRESS_TRIP`
   - executive banner: `EMERGENCY PRESS TRIP`
   - Grafana: line-down / plant-manager action visible

## Result

All 6 scenarios are triggerable and operationally distinct end to end.

The flagship scenario remains the strongest:

- `QUALITY_HOLD_QUENCH` is fully convincing across simulator, API, DB, Svelte, and Grafana
- it shows the clearest operator-to-management story with evidence, hold decision, customer exposure, and recommended action

## Residual Follow-Up Polish

The main runnable path is proven, but one area still carries historical noise:

- `v_aluminium_quality_risk` can include lingering open alerts from prior scenarios
- `v_aluminium_business_risk` therefore remains more portfolio-wide than strictly scenario-local
- open alert counts are inflated by accumulated non-threshold alerts

This does **not** block the runnable demo, because the current active scenario still dominates the banner, action board, and flagship management narrative.

However, the next polish pass should make the secondary risk panels more scenario-local by:

- filtering out stale/non-threshold alert noise
- narrowing quality/business risk rows to the current scenario context

## Exit Criteria Result

- all 6 scenarios are triggerable: yes
- flagship scenario is fully convincing end to end: yes
- weaker secondary-panel behavior is documented explicitly: yes

Checkpoint 8 is complete.
