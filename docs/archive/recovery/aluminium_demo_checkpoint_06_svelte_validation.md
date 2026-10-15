# Checkpoint 6 - Svelte Dashboard Runtime Validation

Date: 2026-04-24

## Objective

Validate the Svelte executive dashboard against the live aluminium demo stack, confirm that scenario switching is coherent in the UI, and remove packaging-era copy from the main dashboard flow.

## Starting Position

- Checkpoint 5 had already proven the live API path:
  - Docker stack up
  - telemetry flowing for all 7 aluminium stations
  - `/api/v1/dashboard` returning live aluminium data
  - scenario switching working at the API level
- The remaining unknown was whether the Svelte dashboard actually rendered and behaved correctly in the browser.

## Issues Found

### 1. Dashboard rendered largely unstyled

The dashboard route and supporting components had been rewritten using utility-class-heavy markup, but this frontend does not currently have the matching Tailwind-style pipeline enabled. The result was a functional data load with poor presentation: cards collapsed into plain text and the dashboard did not look demo-ready.

### 2. `NORMAL` scenario was not truly stable

Clicking `Normal` in the dashboard sometimes left machine-level data in a degraded state even though the banner turned green. The root cause was in the simulator scenario logic:

- `NORMAL` was effectively treated as "release the scenario lock"
- background cycling could still advance machine states after the reset
- UI and telemetry could briefly disagree about whether the line was healthy

### 3. Stale dashboard copy remained

The dashboard footer still referenced `4 named demo states`, which no longer matched the aluminium demo model.

## Fixes Applied

### Dashboard component styling rebuilt with local scoped CSS

The following dashboard-facing components were rewritten to use explicit Svelte-scoped CSS instead of relying on unavailable utility classes:

- `frontend/src/routes/dashboard/+page.svelte`
- `frontend/src/lib/components/ScenarioBanner.svelte`
- `frontend/src/lib/components/FinancialImpactRow.svelte`
- `frontend/src/lib/components/MachineFloorMap.svelte`
- `frontend/src/lib/components/DemoControlPanel.svelte`
- `frontend/src/lib/components/StakeholderColumn.svelte`

This preserved the aluminium dashboard data model while restoring a readable card layout, responsive sections, scenario controls, and a usable floor-map view across desktop and mobile.

### Simulator `NORMAL` scenario behavior corrected

`sim/modbus_sim/scenario_state.py` was updated so that `NORMAL` now returns explicit all-running overrides for every aluminium station instead of falling back to passive background cycling.

Result:

- banner state and telemetry state now agree
- resetting to `NORMAL` clears the live dashboard back to a coherent healthy line
- throughput and fault counts recover correctly after scenario toggles

### Aluminium copy cleaned up

The dashboard footer text was updated from the stale packaging-era wording to:

`6 aluminium demo scenarios, auto-reset 10 min`

## Validation Performed

### Static checks

- `cd frontend && npm run check` -> pass
- `cd frontend && npm run build` -> pass
- `python -m pytest tests/unit -q` -> pass (`35 passed`)

### Runtime verification

The API container was rebuilt so the refreshed static frontend bundle in `services/api/static` matched the rewritten dashboard components.

The dashboard was then exercised against the live stack in the browser flow served from:

- `http://localhost:8080/`

From there, client-side navigation into `Executive View` was verified.

### Browser verification summary

Desktop normal-state checks passed:

- dashboard header visible
- green normal banner visible
- live refresh text visible
- all 7 aluminium stations visible
- updated 6-scenario footer visible
- quality and emergency scenario buttons visible

Desktop `QUALITY_HOLD_QUENCH` checks passed:

- amber quench banner visible
- `QUENCH FLOW LOW` evidence visible
- action text for placing the batch on P2 quality hold visible
- affected-order/customer context visible

Mobile checks passed:

- header visible
- scenario controls visible
- floor-map station names visible

## Residual Caveat

Direct navigation to:

- `http://localhost:8080/dashboard`

still returns a server-side `404`.

The dashboard is currently reachable through the shipped SPA shell at:

- `http://localhost:8080/`

followed by client-side navigation to the dashboard route.

This does not block the demo flow, but it is a deployment/runtime caveat that should be cleaned up later if deep-link support is required.

## Exit Criteria Result

- Dashboard loads with aluminium labels and 6-scenario controls: yes
- Scenario switching updates banner, actions, and floor map coherently: yes
- Core dashboard flow no longer shows packaging-era text: yes

Checkpoint 6 is complete.
