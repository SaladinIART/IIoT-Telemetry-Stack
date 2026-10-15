# Checkpoint 1 Baseline - Aluminium Demo Recovery

Date: 2026-04-24
Repo: `salbotics-iiot-aluminium-demo`
Branch: `main`

## Scope Boundary

In scope:
- Product code
- Product SQL migrations and provisioning
- Product-facing docs and rehearsal content

Out of scope for recovery unless they block validation:
- `.claude/settings.local.json`
- editor-local metadata

## Current Proof Points

- `python -m pytest tests/unit -q` passes: `35 passed`
- changed JSON artifacts parse successfully:
  - `contracts/register_map.json`
  - `infra/grafana/provisioning/dashboards/json/overview.json`
- aluminium domain spec exists:
  - `docs/demo/aluminium_profile_line_spec.md`
- aluminium decision-board migration exists:
  - `db/migrations/008_aluminium_decision_views.sql`
- frontend verification path is currently broken by environment:
  - `frontend/node_modules/acorn/dist/acorn.mjs` missing during `npm run check`

## Changed Repo Files Inventory

Classification legend:
- `implemented`: substantial aluminium conversion is present and internally coherent from static inspection
- `suspected incomplete`: meaningful work is present, but runtime/bootstrap consistency is not yet proven
- `stale-text-only`: mostly copy/documentation drift rather than logic risk

| File | Classification | Reason |
|---|---|---|
| demo rehearsal notes | implemented | aluminium rehearsal content and recruiter/client Q&A are already added |
| `contracts/register_map.json` | implemented | 7-station aluminium line model is present |
| `db/migrations/001_init.sql` | suspected incomplete | foundational seed/schema change needs clean bootstrap proof |
| `db/migrations/002_alerts.sql` | suspected incomplete | alert seed chain not yet validated against new signal catalog |
| `db/migrations/004_api_views.sql` | suspected incomplete | API-facing SQL may still depend on broader migration chain correctness |
| `db/migrations/005_business_context.sql` | suspected incomplete | aluminium business context is present but not boot-verified |
| `db/migrations/006_alert_enhancements.sql` | suspected incomplete | new alert mappings need live DB proof |
| `db/migrations/008_aluminium_decision_views.sql` | suspected incomplete | new decision views exist but are not yet query-verified on a clean DB |
| `docs/demo/aluminium_profile_line_spec.md` | implemented | detailed aluminium narrative and scenario spec are present |
| `frontend/src/lib/components/DemoControlPanel.svelte` | implemented | scenario catalog appears aligned with aluminium demo |
| `frontend/src/lib/components/MachineFloorMap.svelte` | implemented | 7-station aluminium floor map is present |
| `frontend/src/lib/components/ScenarioBanner.svelte` | implemented | aluminium scenario naming is present |
| `frontend/src/lib/types.ts` | implemented | dashboard scenario typing has been relaxed/aligned |
| `frontend/src/routes/dashboard/+page.svelte` | suspected incomplete | core aluminium view is present, but stale footer copy remains |
| `infra/grafana/provisioning/dashboards/json/overview.json` | suspected incomplete | major dashboard rewrite exists, runtime provisioning still unverified |
| `infra/grafana/provisioning/datasources/datasource.yaml` | suspected incomplete | datasource alignment changed, but Grafana load not yet proven |
| `services/api/routers/dashboard.py` | suspected incomplete | aluminium dashboard logic is present, but live DB/API proof is missing |
| `services/api/routers/demo.py` | implemented | scenario endpoint names align with aluminium catalog from static review |
| `services/api/schemas/dashboard.py` | implemented | schema updates are small and appear coherent |
| `sim/modbus_sim/app.py` | implemented | simulator has substantial aluminium telemetry logic |
| `sim/modbus_sim/scenario_state.py` | implemented | 6 aluminium scenarios are present and coherent from static review |

## Known Blockers

### Environment

- `frontend/node_modules` is unhealthy or incomplete:
  - `npm run check` fails on missing `acorn/dist/acorn.mjs`
- full stack boot has not been re-proven after the aluminium conversion

### Code

- migration chain `001 -> 002 -> 004 -> 005 -> 006 -> 008` is not yet validated on a clean database
- Grafana provisioning is edited but not yet runtime-verified
- FastAPI dashboard behavior is edited but not yet runtime-verified
- end-to-end scenario behavior is not yet proven against live data
- `frontend/src/routes/dashboard/+page.svelte` still contains stale footer text: `4 named demo states`

### Documentation

- `README.md` still describes the old 4-asset packaging/REL system
- several runbooks and reference docs still mention feeder/mixer/conveyor/packer examples
- top-level repo narrative does not yet match the current aluminium demo direction

## Checkpoint 1 Result

Checkpoint 1 exit criteria are met:
- there is now a written baseline list for every currently modified or newly added repo file in scope
- blockers are separated into `environment`, `code`, and `documentation`
