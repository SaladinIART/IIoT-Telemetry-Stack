# Condition assessment: steady, stale, unreliable or disconnected?

15 October 2026. Independent Salbotics software experiment. Equipment evidence: **Simulated**. Protocol exchange: real local OPC UA/MQTT connections. No physical furnace, field-data collection, employer inputs or calibrated digital twin.

## Question and method

A furnace temperature stops changing. Before recommending maintenance, distinguish stable operation from frozen acquisition, an unreliable source, a process fault and transport failure.

The custom model uses the existing fictional `furnace-01` contract: two temperatures, a loaded counter, equipment state and fault code. An additional acquisition sequence advances once per simulated acquisition, including unchanged readings. The client resolves namespace URI, checks types/units/read-only access, reads full DataValues and subscribes. Source timestamps are preserved; status and server/receive times stay in diagnostics.

Separate server/client processes were launched by `tools/run_opcua_study.py`. Latest retained run: [run-02 manifest](evidence/2026-10-15-run-02/manifest.json). Earlier [run-01](evidence/2026-10-15-run-01/manifest.json) remains preserved; it predates the final unit/queue-age checks. Do not substitute its source hashes for the latest revision.

Assumptions: deterministic invented equipment values; source interval 1 s; subscription publishing request 500 ms; sequence-progress timeout 5 s; shared local clock. The study runner activates faults after 2 s and records source/runtime hashes. It reports observed behavior, not assumed success.

## Results

| Case | Real retained evidence | Finding | Assessment / next action |
| --- | --- | --- | --- |
| S01 normal, 4 s | [normal.jsonl](evidence/2026-10-15-run-02/normal.jsonl); 20 candidate payloads | Typed reads and notifications reached the client | Baseline acquisition/data mapping working in this local run. |
| S02 steady, 12 s | [steady.jsonl](evidence/2026-10-15-run-02/steady.jsonl); 60 candidates | Temperature SourceTimestamp stayed unchanged; acquisition progressed; no stale diagnostic | Flat value alone is insufficient evidence of failure. Check acquisition independently. |
| S03 frozen, 9 s | [frozen.jsonl](evidence/2026-10-15-run-02/frozen.jsonl); 5 candidates before freeze | Server responsive; acquisition stopped; stale diagnostic about 5.094 s after final sequence notification; no later accepted telemetry | Investigate acquisition/update path before calling this an equipment fault. The ~94 ms excess is observed scheduling delay, not a guaranteed bound. |
| S04 Bad/Uncertain, 4 s each | [bad.jsonl](evidence/2026-10-15-run-02/bad.jsonl), [uncertain.jsonl](evidence/2026-10-15-run-02/uncertain.jsonl); 5 candidates each before injection | Raw non-Good status retained; affected snapshots rejected | Do not invent zero readings or promote Uncertain to good. Investigate source quality. |
| S05 equipment fault, 4 s | [process-fault.jsonl](evidence/2026-10-15-run-02/process-fault.jsonl); 20 candidates | FAULTED state / fault 111 can accompany Good-quality measurements | The measurement may correctly describe an abnormal process. Quality is not equipment condition. |
| S06 server restart | Local integration test plus [retained reconnect trace](evidence/release-verification/reconnect.jsonl) | Real outage observed; new connection/subscription and telemetry after restart | Restore readiness only after fresh acquisition progress; disclose gaps. |
| S07 write rejection | Integration test in [test summary](evidence/release-verification/tests_summary.json) | Correctly typed client write rejected with BadUserAccessDenied; readback not overwritten | Read-only teaching interface demonstrated. This is not penetration testing or security certification. |
| S08 malformed observations | Unit tests in same summary | Missing/naive/pre-epoch time, non-finite values, wrong type, missing node and unknown state rejected | Guard inputs before v2 publication; these negative cases use constructed DataValues, not claims of malformed wire traffic. |
| S09 MQTT outage/recovery | Real isolated broker test; [MQTT trace](evidence/release-verification/mqtt.jsonl) | Broker received valid v2 data; outage publication failed; restarted broker acknowledged publication | Delivery is separate from a candidate payload. Queues bounded; gaps/duplicates possible. |

All six separate-process scenarios passed their declared checks. They produced 115 telemetry candidates in total; the runner did not connect to MQTT. The separate MQTT integration test establishes actual downstream protocol delivery. Its anonymous test broker was restricted to loopback and is not the production broker profile.

Local release regression result: **62 passed** = 53 unit cases (35 existing + 18 new) and 9 new OPC UA/MQTT integration cases. Two added verifier regression cases cover startup gaps/unflushed samples and rejection of missing acknowledgments or mismatched timestamps. Earlier 60-test evidence remains preserved under `evidence/final-verification/`. Raw public experiment files are retained byte-for-byte with SHA-256 manifests; public test summaries derive from actual JUnit output with local host metadata omitted. Original local JUnit remains under ignored `tmp/`. Source code tests do not establish the user's independent understanding.

## Full NEXUS path

Local Docker runtime was unavailable. Remote verification passed in [CI run 38737854129](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/runs/38737854129), testing commit `a9cc81b55d7f15e651048fbb545d3bfb5f41a59c`. All three jobs passed: lint/unit/local protocol tests, frontend build, and OPC UA Stack Trace. [Run metadata](evidence/ci-38737854129/run.json), [collector trace](evidence/ci-38737854129/collector.jsonl) and [verification result](evidence/ci-38737854129/verification.json) are retained with hashes.

The verifier requires a PUBACK-confirmed candidate, the exact matching TimescaleDB row, a successful FastAPI asset request, a provisioned Grafana dashboard and a Grafana datasource query returning the same value. Even a pass does not prove browser pixels, sustained scale, physical equipment behavior or production security.

### Corrections and preserved unsuccessful runs

- [First CI run](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/runs/38737148641): stack trace and frontend passed, overall CI failed because the `pytest` CLI could not import `services`. Adding the repository root to pytest's configured path fixed the reproduced collection error without changing application behavior. Its original [stack result](evidence/ci-38737148641/verification.json) is retained; this does not relabel the overall run as successful.
- [Second CI run](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/runs/38737333052): tests/frontend passed; the stack verifier failed with [JSONDecodeError](evidence/ci-38737333052/verification.json) while ingestion logs showed later rows being written. Code review identified an invalid assumption that the first broker-acknowledged sample must already be stored. The verifier now selects an actual stored row and requires its exactly matching acknowledged candidate; regression tests cover startup loss, ingestion lag and false matches. This is a verifier correction, not a lossless-delivery claim.
- Final CI above passes after both corrections. Prior source traces/results were not rewritten. Core OPC UA runtime hashes in the latest separate-process manifest match committed Git blobs.

## Limitations and engineering judgment

- Small, custom furnace model. No industry companion-specification conformance or OPC certification claim.
- Simulation explores data-handling decisions, not real thermal dynamics, sensor accuracy, equipment wear, calibration or predictive maintenance accuracy.
- Acquisition sequence is an explicit simulator contract. A real source must expose a trustworthy freshness indicator or use another validated acquisition-health strategy.
- No atomic multi-node snapshot, durable backlog, exactly-once delivery or latency guarantee. Subscription queues can discard notifications; local queue overflow forces a fresh connection/readiness cycle. Receive timestamps do not eliminate every possible upstream buffering issue.
- Unsecured loopback teaching endpoint; certificate trust, encrypted transport and authorized real-device integration are future separately scoped work.
- Legacy Modbus collector semantics and B08 findings are preserved. The new adapter's separation of condition/quality does not retroactively repair the legacy path.
- A no-data dashboard cannot determine root cause alone. Consult JSONL and independent checks before suggesting equipment work.

## Interview explanation

“I built a small OPC UA extension for NEXUS using simulated furnace data. I investigated why a flat temperature could mean either stable operation or frozen acquisition, and tested that distinction with a separate acquisition sequence. I also kept source quality separate from equipment faults, retained raw traces, and tested reconnection and MQTT delivery. This is software integration evidence; I would still need device-specific validation before commissioning a real system.”

Learner review remains **NOT ASSESSED**: explain three traces, propose an alternative cause, and modify one scenario before claiming personal mastery.

Standards basis: [OPC Foundation DataValue](https://reference.opcfoundation.org/specs/OPC-10000-4/7.11) and [MonitoredItem model](https://reference.opcfoundation.org/specs/OPC-10000-4/5.13.1). Reproduction instructions: [OPC UA guide](OPCUA_GUIDE.md).
