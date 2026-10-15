# Checkpoint 9 - Documentation and Presentation Cleanup

Date: 2026-04-25

## Objective

Update the repo-facing narrative so the aluminium decision demo is what a reviewer encounters first, instead of older packaging-era examples and stale localhost paths.

This checkpoint was intentionally targeted rather than exhaustive: priority was given to the files most likely to shape first impressions, onboarding, and demo rehearsal.

## Files Updated

### Top-level narrative

- `README.md`
- internal demo rehearsal notes

### Runbooks and references

- `docs/runbooks/01-quickstart.md`
- `docs/runbooks/02-adding-new-asset.md`
- `docs/runbooks/03-alert-tuning.md`
- `docs/runbooks/05-scaling-to-tier3.md`
- `docs/api-reference.md`
- `docs/architecture.md`
- `docs/data-model.md`

## What Changed

### README now reflects the actual aluminium demo

Updated:

- title and opening description
- clone URL to the new public repo
- CI badge to the new public repo
- architecture summary from 4 packaging assets to 7 aluminium stations
- storage section to mention the aluminium decision views
- frontend/grafana descriptions so the executive dashboard + decision board are explicit
- project structure entry for the simulator
- documentation index to include the aluminium line spec

The README now presents the repo as an aluminium decision demo first.

### Demo rehearsal notes aligned to the actual runnable flow

Internal rehearsal notes were updated so the Svelte flow points to:

- `http://localhost:8080/`
- then navigation to **Executive View**

The stale REL-branding note was also rewritten into a generic static-assets rebuild note.

### Quickstart now rehearses the real flagship flow

`docs/runbooks/01-quickstart.md` was updated to:

- use the new repo URL
- describe 8 services correctly
- show aluminium telemetry examples
- expect 7 aluminium stations instead of 4 packaging assets
- use the demo scenario API for `QUALITY_HOLD_QUENCH` instead of injecting fake telemetry rows directly
- point users to the actual dashboard flow:
  - web app at `http://localhost:8080/`
  - Grafana at `http://localhost:3000`

### Examples in operational docs were de-packaged

Updated examples now use aluminium-appropriate assets/signals such as:

- `quench-01`
- `press-01`
- `ageing-01`
- `quench_flow_lpm`
- `oven_temp_c`

This affected:

- `02-adding-new-asset.md`
- `03-alert-tuning.md`
- `api-reference.md`
- `data-model.md`

### Architecture and data-model docs now mention the decision board

`docs/architecture.md` and `docs/data-model.md` now explicitly describe:

- the 7-station aluminium simulator
- the executive dashboard route
- the Grafana aluminium decision board
- the aluminium-specific decision views:
  - `v_aluminium_line_current_state`
  - `v_aluminium_decision_board`
  - `v_aluminium_quality_risk`
  - `v_aluminium_business_risk`

### Stale localhost paths were normalized

High-traffic docs were updated from stale `http://localhost:8000` references to the current exposed API/UI path:

- `http://localhost:8080`

## Validation

A final search across the targeted top-level docs and runbooks found no remaining matches for:

- `feeder-01`
- `mixer-01`
- `conveyor-01`
- `packer-01`
- `packaging-line-1`
- `REL-2000`
- `http://localhost:8000`
- old repo names in the targeted docs

## Result

The repo now presents itself primarily as the aluminium profile decision demo rather than the earlier packaging prototype.

Remaining possible follow-up polish:

- refresh screenshot assets in `docs/screenshots/` to match the current aluminium UI surfaces
- expand the API reference further if the demo-specific endpoints need full request/response examples

Checkpoint 9 is complete.
