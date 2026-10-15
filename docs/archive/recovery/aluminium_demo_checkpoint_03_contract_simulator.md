# Checkpoint 3 - Contract and Simulator Alignment

Date: 2026-04-24
Repo: `salbotics-iiot-aluminium-demo`

## Objective

Validate that the aluminium register contract, simulator scenario model, and scenario API all agree on:
- 7 stations
- 20-word address stride
- signal layout
- state and fault code usage
- 6 named scenarios
- flagship `QUALITY_HOLD_QUENCH` telemetry signature

## Files Checked

- `contracts/register_map.json`
- `sim/modbus_sim/scenario_state.py`
- `sim/modbus_sim/app.py`
- `services/api/routers/demo.py`
- `docs/demo/aluminium_profile_line_spec.md`

## Validation Results

### Register contract

- Asset count: `7`
- Asset order:
  - `furnace-01`
  - `press-01`
  - `quench-01`
  - `cooling-01`
  - `stretcher-01`
  - `saw-01`
  - `ageing-01`
- Base addresses: `0, 20, 40, 60, 80, 100, 120`
- Address stride check: passed
- Every asset uses the same 8-word layout:
  - primary signal at offset `0`
  - secondary signal at offset `2`
  - counter at offset `4`
  - `state_code` at offset `6`
  - `fault_code` at offset `7`

### Scenario model

- Scenario count: `6`
- Scenario names:
  - `NORMAL`
  - `QUALITY_HOLD_QUENCH`
  - `PRESS_BOTTLENECK`
  - `STRETCHER_BACKLOG`
  - `AGEING_OVEN_DEVIATION`
  - `EMERGENCY_PRESS_TRIP`
- Every scenario covers the same 7 asset ids as the register map
- `SCENARIO_HEALTH` keys match the scenario catalog
- `SCENARIO_MESSAGES` keys match the scenario catalog

### API alignment

- `services/api/routers/demo.py` exposes the same 6 scenario names
- No naming drift was found between the API scenario whitelist and the simulator scenario catalog

### Flagship scenario check

`QUALITY_HOLD_QUENCH` is represented in code, not only in docs.

Static verification from `sim/modbus_sim/app.py`:
- baseline quench flow centers around `220 lpm`
- baseline quench exit temperature centers around `58 C`
- when `fault_code == 311`:
  - `quench_flow_lpm` drops to about `148 lpm`
  - `exit_temp_c` rises to about `94 C`

This matches the design narrative in `docs/demo/aluminium_profile_line_spec.md`:
- flow below the `180 lpm` warn floor
- exit temp above the `80 C` warn ceiling

## Outcome

Checkpoint 3 exit criteria are met from static and structured validation:
- no mismatch was found between register map, simulator scenario catalog, and API scenario names
- 7-station stride assumptions are internally consistent
- the flagship `QUALITY_HOLD_QUENCH` correlated telemetry signature is encoded in simulator logic

## Remaining Boundary

This checkpoint does not prove runtime boot or live Modbus polling. Those belong to later checkpoints:
- database bootstrap
- API runtime
- Grafana runtime
- end-to-end scenario execution
