# NEXUS OPC UA case: can we trust this furnace reading?

> Historical U01 planning snapshot. On 15 October 2026 the user authorized consolidation into `SaladinIART/IIoT-Telemetry-Stack` and direct Codex implementation/publication of the full batch. Current status, ownership and commands: `CONSOLIDATION_PLAN.md`, `OPCUA_GUIDE.md` and `CONDITION_ASSESSMENT.md`. Earlier Claude dispatch and stop instructions below are superseded for that approved batch; original planning context is retained.

Date: 2026-10-15. U01: planning deliverable complete; implementation NOT STARTED.

## User decisions and purpose

Extend NEXUS directly. Start with read-only data and subscriptions. No hardware purchase required. Codex plans/reviews; Claude Code implements one authorized checkpoint at a time. Proposed technical defaults below remain reviewable; this document does not authorize the remaining checkpoints, dependency installation, hardware operations, publication or push.

Build an independently invented furnace-monitoring case: an operator sees a temperature that has stopped changing. Is the process stable, acquisition frozen, the source reporting unreliable data, or the connection down? Demonstrate how to distinguish these conditions before making a maintenance recommendation.

Intended evidence: a real local OPC UA client/server connection carrying simulated equipment data; structured fault experiments; a traceable condition-assessment report. This does not establish physical furnace condition, field-data collection, production commissioning, a calibrated digital twin, or independent user competence.

## U01 acceptance and repository baseline

- PASS: inspected relevant repositories; no runnable OPC UA implementation found in inspected paths. This is a bounded inventory, not an exhaustive account-wide guarantee.
- PASS: NEXUS selected by user; read-only subscriptions selected by user.
- PASS: source signals, interface proposal, learning outcomes and test scenarios recorded.
- PASS: checkpoints and cross-model handoff recorded; stop before U02.
- Not assessed: runtime, dependency compatibility, network security, full pipeline, learner performance.

Checkout: `C:/Users/salbot01/Salbotics/salbotics-iiot-aluminium-demo`.
Branch at inspection: `codex/equipment-fault-evidence`; HEAD `fb430f567cd7a7b4b1f8a0bec3e341741b8d97d5`; initially clean. Preserve existing B08 findings and original Modbus behavior.

Evidence inventory:

| Evidence | Visibility | Finding |
| --- | --- | --- |
| [NEXUS repository](https://github.com/SaladinIART/salbotics-iiot-aluminium-demo) | Public; inspected local checkout | `services/collector/app.py` uses Modbus and MQTT; inspected `pyproject.toml` has no OPC UA library. |
| [PLC Learning Hub](https://github.com/SaladinIART/salbotics-plc-learning-hub) | Public | `docs/PHASE2_3_OVERVIEW.md` explicitly excludes OPC UA server/client runtime. Theory is not runtime evidence. |
| IIoT-Telemetry-Stack, factory-energy-monitor, edge-telemetry-platform | Public; relevant paths inspected | No runnable OPC UA implementation identified in inspected material. |
| NEXUS B08 review/probe | Local | Offline baseline only; complete Docker/broker/database/dashboard path remains unverified. |
| This case and node contract | Local, new proposal | Requirements and Assumptions only; no experiment results yet. |

The direct `/projects` web fetch failed during this investigation. Findings above rely on repository inspection, not a claimed live-page audit. No private/employer material belongs in this case.

## Proposed system and boundaries

`Fictional furnace simulator -> OPC UA server -> OPC UA subscription client -> NEXUS MQTT -> existing ingestion/DB/Grafana`

1. Use the existing `furnace-01` identity, temperatures, loaded count, state and fault codes in `contracts/register_map.json`.
2. Add an optional OPC UA path alongside the Modbus path. Only one collector may publish this asset in a selected run. Defaults and existing tests remain unchanged.
3. Python `asyncua` is the proposed library, subject to Python 3.13 compatibility and a tested version pin in U02. No package was installed for U01.
4. First proof uses two local processes and a loopback endpoint. Broker, database and dashboard integration are later, separately verified evidence.
5. Client access is read-only. Server-internal scenario updates are allowed. No externally callable control/reset method, setpoint write, PLC connection or physical actuation.
6. First profile is an explicitly unsecured loopback teaching endpoint. Do not bind it to a LAN or advertise production security. Certificate-based operation is a separate optional extension requiring its own brief and real trust-rejection tests.
7. Keep Svelte frozen. Use CLI evidence first and existing Grafana for the later operator view. Do not migrate unrelated stack components.

These are OPC UA client/server subscriptions, not OPC UA PubSub. MQTT remains the downstream transport; neither protocol needs to replace the other.

## Know-how: concepts the learner must explain

- **Address space:** browse an equipment object, identify variables by stable string NodeId and namespace URI, inspect type and units. Resolve namespace indexes at runtime rather than assuming `ns=2`.
- **Acquisition versus delivery:** sensor sampling, monitored-item sampling and subscription publishing are different activities. Record requested and server-revised intervals; a subscription is not a guarantee that every sample arrives.
- **Data quality:** inspect each OPC UA DataValue status before using its numeric value. A real equipment fault can still have Good-quality measurements.
- **Time:** preserve the received SourceTimestamp; log ServerTimestamp and local receive time separately. Missing/invalid timestamps must not silently become acquisition time 'now'.
- **Freshness:** an unchanged value or old SourceTimestamp alone does not prove failure. Use a separately defined acquisition sequence that advances on each simulated acquisition, even when temperature stays constant. A subscription keepalive proves session activity, not source acquisition.
- **Assessment:** compare baseline and injected conditions, identify supporting observations, recommend the next check, and state uncertainty. A synthetic fault is not a measured real failure.

Official references, checked 2026-10-15:

- [OPC Foundation: OPC UA](https://opcfoundation.org/about/opc-technologies/opc-ua/).
- [Part 4, DataValue](https://reference.opcfoundation.org/specs/OPC-10000-4/7.11): values, status and timestamps.
- [Part 4, MonitoredItem model](https://reference.opcfoundation.org/specs/OPC-10000-4/5.13.1): sampling, filters and notifications.
- [FreeOpcUa asyncua source/documentation](https://github.com/FreeOpcUa/opcua-asyncio): proposed Python implementation, not an endorsement of an untested release.

## Proposed interface rules

Machine-readable draft: `OPCUA_NODE_CONTRACT.json` in this directory. Existing numeric telemetry v2 schema has `additionalProperties: false`; raw OPC UA status and server timestamps therefore belong in a separate diagnostic artifact, not invented payload fields.

| Input condition | Proposed handling |
| --- | --- |
| Good, finite value, valid timestamp and fresh acquisition | Build existing telemetry v2 with explicit `source_ts`, `quality=good`; preserve equipment state independently. |
| Bad or Uncertain status | Suppress current numeric telemetry; record raw status, node, timestamps and reason in diagnostics. No zero substitution. Uncertain is not silently promoted to good. |
| Missing source timestamp, wrong type, unknown state code, non-finite number | Reject/diagnose; no fallback acquisition timestamp. |
| Acquisition sequence advances while temperature stays constant | Healthy steady process; retain original value timestamp if unchanged. |
| Acquisition sequence fails to advance beyond configured timeout | Diagnose acquisition stale and suppress normal good publication until recovery. Do not invent a fresh value or translate this to equipment FAULTED/999. |
| Server/network unavailable | Diagnose transport unavailable, clear readiness and re-establish subscription before resuming. |
| MQTT unavailable | Record publication failure/gap explicitly; bounded memory only. No exactly-once, lossless or persistent-backlog claim. |

Initial Assumptions: source acquisition every 1 s; requested subscription publishing every 500 ms; acquisition timeout 5 s, measured with client monotonic time. These are teaching settings, not industrial specifications. Reset freshness on disconnect and require observed acquisition progress after startup/reconnect. Record clock assumptions for UTC timestamps.

There is no atomic multi-node snapshot guarantee. Stage updates and publish only after required state/fault metadata is valid for the current connection and acquisition is fresh. If acquisition coherence is required, implement and test an explicit simulator snapshot protocol in a separate checkpoint; do not claim coherence from subscription callback order.

## How-to: reproducible investigation

Commands and file names below U02 are implementation targets, not commands already available. Each implementer must supply exact commands and retained outputs in its return.

1. Establish Python/runtime availability; create an isolated optional dependency environment only when authorized. Pin the tested library. Keep runtime tools free and local.
2. Start the deterministic server using a recorded scenario and seed. Browse the address space with the new client; retain node identifiers, types, access and units.
3. Read full DataValues, then subscribe. Retain statuses, source/server/receive timestamps, acquisition sequence and actual negotiated settings. This proves real protocol traffic with simulated process inputs.
4. Run one scenario at a time using server startup configuration or local scenario controls. No client writes to equipment nodes.
5. Assess observations against the matrix below. Preserve actual logs even if a result fails. Fixes require a new run identifier; never replace a failed run with an edited success log.
6. Only after local protocol acceptance, bridge approved payloads through MQTT and verify one received sample against the schema, database row and Grafana view. Missing Docker or broker means integration NOT VERIFIED, not a successful simulated integration.
7. Write a report with question, requirements/assumptions, method, evidence, findings, alternative explanations, recommendation and limitations. Separate observed protocol behavior from simulated equipment condition.

| Scenario | Deliberate condition | Required observation / assessment |
| --- | --- | --- |
| S01 baseline | Changing finite temperatures; sequence advancing | Typed reads and notifications; normal publication eligible. |
| S02 steady | Temperature constant for at least 10 s; sequence advancing | No false stale assessment; old value timestamp may be valid. |
| S03 frozen acquisition | Sequence stops, server remains responsive | Stale after configured timeout plus recorded scheduling tolerance; distinguish from connection loss. |
| S04 unreliable source | Inject Bad then Uncertain status | Raw codes retained; no fabricated/good numeric publication. |
| S05 process fault | Valid temperatures; equipment state FAULTED and fault 111 | Source quality can remain Good; explain process fault separately. |
| S06 transport | Stop/restart server | Outage diagnosed; new initial read and restored monitored items; recovery/gap documented. |
| S07 access | Attempt client write with correct value type | Server rejects write; readback unchanged by attempted write. |
| S08 malformed input | Missing timestamp, NaN/Infinity, wrong type, unknown state | Adapter rejects/diagnoses each; deterministic offline cases acceptable when transport cannot encode an invalid input. |
| S09 downstream | Stop/restart MQTT broker | Failure and data gap disclosed; documented recovery; no hidden replay/lossless claim. |

For each run retain: run ID, source revision and changed-file hashes, scenario/seed, environment and package versions, command, UTC start/end, raw diagnostic/payload evidence, actual outcome, pass/fail rationale and limitations. Use local files; redact credentials/endpoints before public release.

## Report and portfolio story

Working title: **NEXUS: assessing equipment-data reliability with OPC UA**.

Once supported by real runs: 'Built a local OPC UA monitoring extension for NEXUS using simulated furnace data. Investigated steady versus stale readings, source quality and reconnect behavior; documented condition-assessment decisions and limitations.'

Before implementation, describe this as a planned case. Never call synthetic inputs field measurements or convert a software exercise into physical commissioning experience. Do not date it as past client delivery. User ownership and learning can be demonstrated by explaining a trace and modifying one scenario without an agent doing the explanation.

Interview questions: Why can a flat temperature still be healthy? What does Good status mean during an over-temperature fault? What information is lost in v2 mapping? What proves the source is acquiring? What happens during a connection gap? Why use OPC UA upstream and MQTT downstream?

## Checkpoint master list and continuation

Token estimates cover implementation/self-checks/handoff per checkpoint; independent Codex review adds roughly 1-3k each. They are planning estimates, not measured usage. Next-step recommendation: Claude Code Sonnet 5.5 Medium, matching the user's established workflow; verify the actual UI model/effort and record UNKNOWN when unavailable. No new capability or pricing claim is implied.

| CP | Goal | Acceptance criteria | Recommended model | Token estimate | Status | Model used |
| --- | --- | --- | --- | --- | --- | --- |
| U01 | Define bounded engineering case | Inventory, node draft, experiments and handoff present; no runtime claim | Codex review/planning | 3-5k | COMPLETE: documents only | Codex; exact variant unavailable |
| U02 | Read-only local server | Optional tested dependency pin; typed furnace address space; separate client reads and rejected write demonstrated | Sonnet 5.5 Medium | 3-5k | PROPOSED | — |
| U03 | Browse/read/subscribe client | URI-resolved nodes; full DataValues and revised intervals logged; real local notifications retained | Sonnet 5.5 Medium | 3-5k | PROPOSED | — |
| U04 | Validate and map observations | Existing v2 builder reused; status/timestamps/types/state guards; negative cases; no schema widening | Sonnet 5.5 Medium | 3-5k | PROPOSED | — |
| U05 | Assess freshness | Deterministic steady/frozen scenarios; sequence-based timeout; no flat-value false positive; readiness rules tested | Sonnet 5.5 Medium | 3-5k | PROPOSED | — |
| U06 | Recover OPC UA session | Real server restart; subscription/readiness recovery; gaps and bounded retry documented | Sonnet 5.5 Medium | 3-5k | PROPOSED | — |
| U07 | Bridge to MQTT | Optional collector entry point; real broker validates v2 topics/payloads; outage behavior and single-publisher rule verified | Sonnet 5.5 Medium | 3-5k | PROPOSED | — |
| U08 | Verify operator pipeline | Opt-in wiring; one payload traced to DB/Grafana; outage visible; existing Modbus baseline preserved; unavailable runtime remains unverified | Sonnet 5.5 Medium | 4-6k | PROPOSED | — |
| U09 | Write condition-assessment report | S01-S09 evidence matrix; raw runs linked; failures/limitations retained; user explanation recorded separately | Sonnet 5.5 Medium + Codex review | 3-5k | PROPOSED | — |
| U10 | Prepare portfolio integration | Accurate README/case draft and links; claims match accepted runs; publication remains gated | Sonnet 5.5 Medium + Codex review | 2-4k | PROPOSED | — |

Local demonstration milestone: U02-U06. Full NEXUS/report milestone: U07-U09. Portfolio draft: U10. Certificate/security, physical PLCs and digital-twin calibration require separately scoped future briefs.

Each CP targets 1-3 implementation/test files. Keep this master status canonical; record actual changed paths/results in a dated section of GEMINI.md, not a proliferation of duplicate trackers. If scope exceeds 3 meaningful files, propose a split before proceeding. Implementers self-check; Codex accepts or returns findings before dependent work.

### Next dispatch — U02 only, after user continuation

> Work in C:/Users/salbot01/Salbotics/salbotics-iiot-aluminium-demo. Read AGENTS.md, GEMINI.md, docs/opcua/U01_STUDY_CASE.md and OPCUA_NODE_CONTRACT.json. Implement U02 only. Check git status first and preserve unrelated work. Verify the frozen source hashes before relying on the draft contract; report drift instead of overwriting it. Proposed scope: pyproject.toml optional OPC UA dependency, services/opcua_demo/server.py, tests/integration/test_opcua_demo_server.py. Follow existing Python 3.13 stack. Verify a supported library version before selecting a pin; use an isolated environment only when installation is authorized. Build typed read-only nodes and deterministic startup scenarios for one furnace; keep endpoint on loopback. Test separate-client reads and a correctly typed client write rejected by server; record actual status and unchanged readback. Do not change the legacy collector or telemetry schema. Keep real traffic and mocked tests labelled separately. Append U02 results, commands, versions, changed files, limitations and model/effort to GEMINI.md. Mark READY_FOR_REVIEW, not COMPLETE. No hardware, spend, commit, push, publication or U03. Stop if a prerequisite is missing; do not invent successful evidence.

U01 actual token expenditure: not exposed by the session. No runtime tests were performed; document/JSON consistency checks only.
