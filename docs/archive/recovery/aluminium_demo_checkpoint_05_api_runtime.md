# Checkpoint 5 - API and Runtime Validation

Date: 2026-04-24

## Goal

Validate the live FastAPI responses against a running aluminium stack and confirm that the dashboard is populated from real simulator and database activity rather than fallback placeholders.

## Runtime fixes made during this checkpoint

1. Restored simulator compatibility by pinning `pymodbus==3.8.3` in `pyproject.toml`.
2. Updated `sim/modbus_sim/app.py` to use the `ModbusSlaveContext` / `ModbusServerContext(slaves=...)` API expected by the pinned server version.
3. Updated `services/collector/app.py` to call `read_holding_registers(..., slave=...)` instead of the unsupported `device_id=...` keyword.
4. Updated runtime defaults from packaging to aluminium in:
   - `src/iiot_stack/settings.py`
   - `.env.example`

## Verification performed

### Services

`docker compose ps` showed all required services up:

- `iiot-modbus-sim`
- `iiot-collector`
- `iiot-ingestor`
- `iiot-api`
- `iiot-alerting`
- `iiot-timescaledb`
- `iiot-mosquitto`
- `iiot-grafana`

### Health and scenario API

- `GET http://localhost:8080/health` -> `{"status":"ok"}`
- `GET /api/v1/demo/scenario` returned the aluminium scenario catalog and current active scenario
- `POST /api/v1/demo/scenario/QUALITY_HOLD_QUENCH` succeeded and returned:
  - `scenario = QUALITY_HOLD_QUENCH`
  - `health = AMBER`
  - the expected quench-hold narrative

### Telemetry flow

Collector logs confirmed live publishes for all seven stations and their five signals:

- furnace-01
- press-01
- quench-01
- cooling-01
- stretcher-01
- saw-01
- ageing-01

Ingestor logs confirmed nonzero telemetry batches reaching TimescaleDB.

Direct DB check showed telemetry rows present for aluminium assets/signals, for example:

- `furnace-01 / billet_temp_c`
- `press-01 / ram_force_kn`
- `quench-01 / quench_flow_lpm`
- `ageing-01 / aged_batch_count`

### Dashboard API

`GET /api/v1/dashboard` now returns live aluminium data.

Under `NORMAL`:

- `scenario = NORMAL`
- all seven assets reported `RUNNING`
- `throughput_pct = 100.0`
- `units_today` advanced from live telemetry

Under `QUALITY_HOLD_QUENCH`:

- `scenario = QUALITY_HOLD_QUENCH`
- `health = AMBER`
- `quench-01` reported `FAULTED` with `fault_code = 311`
- `throughput_pct = 85.7`
- `current_mttr_estimate_min = 30`
- logistics shifted `Automotive Customer B` and `MNC Customer A` to `MONITORING`

## SQL-backed response check

The dashboard recommended actions are coming from the SQL decision view, not the Python fallback:

- `v_aluminium_decision_board` returned four rows for `QUALITY_HOLD_QUENCH`
- those same action texts appeared in `/api/v1/dashboard`

This confirms the API is consuming the live DB decision surface correctly.

## Residual issue to carry forward

`v_aluminium_quality_risk` remained empty during `QUALITY_HOLD_QUENCH` even though:

- the simulator faulted `quench-01`
- the dashboard reflected the hold scenario correctly
- `v_aluminium_decision_board` returned the expected quench-hold actions

This does not block Checkpoint 5 because the API contract and dashboard response are now live and aluminium-specific, but it is a real follow-up item for later runtime/Grafana proof because Grafana is expected to lean on the quality-risk view.

## Exit criteria result

- API endpoints return aluminium-line data and scenario names: yes
- dashboard response is populated from live DB data: yes
- packaging-era runtime defaults leaking into the live API path: corrected

Checkpoint 5 status: complete
