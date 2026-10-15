# B08 — NEXUS diagnostic evidence baseline (offline)

Date: 15 October 2026. Author: Claude Sonnet 5.5 via Claude Code (user-authorized
batch B04–B12). Status: READY_FOR_REVIEW, provisional until independent review.
Builds on the existing `docs/career-readiness/CP1_BASELINE.md` (14 October);
that file and `CP1_EVIDENCE.json` are preserved unchanged.

## Scope and evidence labels

One offline scenario family: the **real** `services/collector/app.py::run()`
executed unmodified, with only its external edges faked (Modbus client, MQTT
client, clock/sleep). Evidence level: **Simulated component** result plus
**code inspection**. Docker, broker, ingestor, database, API and dashboard were
**not** run, so nothing here is an end-to-end result.

- Checkout: `C:/Users/salbot01/Salbotics/salbotics-iiot-aluminium-demo`, branch
  `codex/equipment-fault-evidence`, HEAD `8e50fbc`. Pre-existing dirty state
  (`GEMINI.md` modified, `docs/career-readiness/` untracked) preserved; frontend
  untouched (frozen legacy).
- `services/collector/app.py` SHA-256 `87b8bd4b…04a2d` (identical to CP-1 record).
- Existing unit tests, project venv: `pytest tests/unit` → 35 passed (0.61 s).
- Probe: [`../b08_collector_probe.py`](../b08_collector_probe.py);
  output [`collector_probe.json`](collector_probe.json)
  (SHA-256 `286fb77c…df2da`). Reproduce:
  `.venv/Scripts/python.exe docs/career-readiness/b08_collector_probe.py --output <new path>`.

## Question

Can an operator tell apart (a) an **equipment fault**, (b) a **transport
failure** and (c) **stale data** from what the collector publishes?

## Observed collector outputs (Simulated component)

Asset under test `furnace-01` (7 assets polled). `state` / `fault_code` /
`quality` are the published payload fields.

| Scenario | Telemetry (state, fault, quality) | Events published | Observation |
|---|---|---|---|
| Normal | RUNNING, 0, good | `state_changed`; `status` RUNNING/0 | baseline |
| Equipment fault (PLC reports FAULTED, code 113 BURNER_TRIP) | FAULTED, 113, **bad** | `alarm_raised` (113, BURNER_TRIP) **and** `status` FAULTED/**999** | one equipment fault produces two different fault codes |
| Maintenance (PLC state MAINTENANCE) | MAINTENANCE, 0, **stale** | `maintenance_started`; `status` FAULTED/**999** ("collector status is stale") | "stale" means *maintenance*, and a maintenance state is reported as FAULTED/999 |
| Transport: Modbus connect fails | none published | `status` FAULTED/**999** for all 7 assets | transport loss is labelled with the same state word (FAULTED) as an equipment fault, with code 999 instead of an equipment code |
| Transport: read error on one asset | assets before the failure: normal telemetry; failing asset and all later ones: no telemetry | `status` FAULTED/999 for **every** asset, including ones that had just read fine | one bad read marks the whole line FAULTED for that cycle |
| Frozen source values; clock advances 300 s per poll | RUNNING, 0, **good** each time | no stale/age event | data stamps are refreshed at poll time (3 distinct `source_ts` across 4,200 s) so frozen source data are indistinguishable from live data |

## What can and cannot be distinguished

| Condition | Distinguishable from the published stream? | Basis |
|---|---|---|
| Equipment fault | Yes, by `alarm_raised` + equipment `fault_code` (111–113 etc.) and telemetry quality `bad` | Simulated component |
| Transport failure | Partly: only `fault_code` 999 / `reason_code` collector_status; state field says FAULTED like an equipment fault | Simulated component |
| Maintenance | Partly: telemetry quality `stale` and `maintenance_started`; but `status` says FAULTED/999 | Simulated component |
| Data age / frozen values | **No.** `stale` is assigned from the maintenance *state*; the collector computes no age and `source_ts` is the poll time | Simulated component + code inspection (`app.py` quality mapping) |

## Code-inspection observations (not run)

- `services/alerting/detector.py` documents that only `good`-quality samples
  are evaluated, so during equipment fault, maintenance or a transport failure
  threshold/statistical alerts are intentionally not raised from those
  samples; the *fault itself* is only visible through the collector's events.
  How the router/API presents these was not exercised.
- The API exposes `quality` and `last_seen`; whether the dashboard distinguishes
  "no data for a long time" from "FAULTED" was not run (frontend is frozen,
  Docker unavailable in CP-1).

## Component versus end-to-end

| Layer | Status |
|---|---|
| Collector logic (fault/maintenance/transport/frozen) | Observed here, faked edges |
| Scenario API normal → quench → reset | Observed in CP-1 (Flask test client) |
| Unit tests (35) | Passed here |
| Modbus ↔ MQTT ↔ ingestor ↔ DB ↔ API ↔ dashboard | **Not run** |

## Limitations

- Faked Modbus returns synthetic registers; real PLC/Modbus timing, retained
  MQTT messages and broker behaviour are unobserved.
- The probe shares the collector's `StopProbe` exit via `BaseException`; its
  fakes do not model reconnect timing (backoff delays were replaced by the
  fake clock).
- No fix was attempted. Candidate repairs (separate `communication`, `data_age`
  and `equipment_state` fields; a status code that is not FAULTED for
  maintenance; per-asset instead of per-cycle failure marking) are proposals
  for a separately scoped checkpoint and need contract/schema review.
- Learner NOT ASSESSED. Suggested exercise: predict the three published codes
  for a connect failure versus a BURNER_TRIP, then run the probe.
