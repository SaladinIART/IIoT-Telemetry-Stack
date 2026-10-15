# Checkpoint 4 - Database and Migration Validation

Date: 2026-04-24
Repo: `salbotics-iiot-aluminium-demo`

## Objective

Validate the active migration chain as a sequence, not as isolated files:

- `001_init.sql`
- `002_alerts.sql`
- `003_site_config.sql`
- `004_api_views.sql`
- `005_business_context.sql`
- `006_alert_enhancements.sql`
- `007_fix_kpi_view.sql`
- `008_aluminium_decision_views.sql`

Confirm:
- no active migration path still depends on the old packaging assets
- the clean database bootstrap succeeds from zero
- aluminium decision views are present and queryable

## Static Sweep

Searched the migration folder for stale packaging references:
- `feeder-01`
- `mixer-01`
- `conveyor-01`
- `packer-01`
- `packaging-line-1`
- `REL-2000`

Result:
- no old packaging asset or line-name references were found in the active migration chain
- the only remaining hits from earlier broader scans were non-problem strings outside this DB validation scope

## Clean Bootstrap Method

Used a disposable TimescaleDB container with the repo migrations mounted into
`/docker-entrypoint-initdb.d`:

- image: `timescale/timescaledb:latest-pg16`
- DB: `iiot`
- user: `iiot`
- mounted migrations directory: `db/migrations`
- host port: `55432`

This validates the same initialization model the compose stack uses for a fresh volume.

## Bootstrap Result

The clean init completed successfully.

Observed in the init logs:
- `001_init.sql` applied
- `002_alerts.sql` applied
- `003_site_config.sql` applied
- `004_api_views.sql` applied
- `005_business_context.sql` applied
- `006_alert_enhancements.sql` applied
- `007_fix_kpi_view.sql` applied
- `008_aluminium_decision_views.sql` applied

No migration dependency failure occurred.

## Runtime Queries

### Seeded metadata

`asset_metadata` returned exactly 7 aluminium assets, all under:
- `aluminium-profile-line-1`

### Required aluminium views

All required views exist and are queryable:
- `v_aluminium_line_current_state`
- `v_aluminium_decision_board`
- `v_aluminium_quality_risk`
- `v_aluminium_business_risk`

### Behavior notes

On a fresh boot with no telemetry yet:
- `v_aluminium_line_current_state` returns 7 rows with `UNKNOWN` per-asset state and line rollup `GREEN/NORMAL`
- `v_aluminium_decision_board` returns the `NORMAL` decision rows
- `v_aluminium_quality_risk` is empty, which is expected without open alerts
- `v_aluminium_business_risk` is empty, which is expected without computed at-risk orders

This means the views are available and internally resolvable even before live simulator data arrives.

## Outcome

Checkpoint 4 exit criteria are met:
- a clean database boot applies the migration chain successfully
- the four aluminium decision views are present and queryable
- no active DB migration path still depends on feeder/mixer/conveyor/packer naming

## Remaining Boundary

This checkpoint proves schema/bootstrap correctness, not live application behavior.
Still deferred to later checkpoints:
- API runtime against live DB data
- Grafana runtime provisioning
- end-to-end scenario execution with simulator telemetry
