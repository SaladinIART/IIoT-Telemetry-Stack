# Canonical NEXUS consolidation and OPC UA batch

15 October 2026. User explicitly authorized making IIoT-Telemetry-Stack canonical, preserving the aluminium repository, implementing the planned read-only extension, and publishing README/About/wiki updates in one batch. This supersedes the prior Claude implementation dispatch and one-checkpoint stop for this batch. Codex implements and reviews directly; no Claude run is used.

## Provenance and preservation

- Original target main: `99f44045ae06f61715c55f4322b528f101aa10ae`.
- Aluminium remote main: `8e50fbc8e217fc0d149d601b14fec0cc6a507ff9`.
- Later local accepted baseline: `fb430f567cd7a7b4b1f8a0bec3e341741b8d97d5`.
- `git merge-base` confirmed target `99f4404` is an ancestor of the local baseline. Imported by fast-forward on `codex/nexus-opcua-consolidation`; no unrelated-history merge, deletion or force-push needed.
- Imported existing frontend work and compiled assets unchanged; no new Svelte functionality. Existing Python files received mechanical lint/format cleanup to make existing CI gates pass. B08's original result artifacts stay unchanged.
- Prior local U01 plan/node draft copied from the aluminium checkout. Its baseline hashes are historical: Python formatting and the optional dependency change intentionally alter some current files. Do not treat that historical snapshot as the current runtime manifest.
- Aluminium repository and its dirty local U01 documents are preserved; this update does not write to that checkout or change its remote.

## Checkpoint master list

All rows use Codex directly. Exact session model variant and actual token usage are unavailable; recommended model is the current Codex implementation/review session. Estimates are planning ranges, not measured usage. Each row is one outcome, usually 1-3 principal code/test files; documentation/handoff is shared. User authorized running the complete batch.

| CP | Goal | Acceptance criteria | Recommended model | Token estimate | Status | Model used |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | Consolidate history | Ancestor verified; later NEXUS history retained; aluminium source preserved | Codex | 1-2k | COMPLETE locally | Codex |
| M02 | Furnace node model/server (U02) | Typed nodes, loopback-only, real reads, server rejects client writes | Codex | 2-4k | PASS local tests | Codex |
| M03 | Browse/read/subscribe (U03) | URI resolution; type/unit/access checks; raw DataValues and revised publish settings retained | Codex | 2-4k | PASS local tests | Codex |
| M04 | v2 adapter (U04) | Source timestamps preserved; Bad/Uncertain/type/number/state/timestamp guards | Codex | 2-3k | PASS local tests | Codex |
| M05 | Source freshness (U05) | Steady accepted; frozen rejected; post-connection progress required | Codex | 1-3k | PASS local tests and retained runs | Codex |
| M06 | OPC UA recovery (U06) | Real server restart; new subscription and accepted samples after recovery | Codex | 1-3k | PASS local integration | Codex |
| M07 | MQTT bridge (U07) | Real broker receives v2; outage publication fails; recovery gets PUBACK | Codex | 2-4k | PASS local integration | Codex |
| M08 | Opt-in operator pipeline (U08) | Single collector overlay; exact payload-to-DB/Grafana trace and API check | Codex | 2-4k | CONFIGURED; CI verification pending | Codex |
| M09 | Condition report (U09) | Six separate-process runs, raw evidence, hashes and bounded conclusions | Codex | 2-4k | Prepared; final review pending | Codex |
| M10 | Public documentation (U10) | Canonical README, guide, wiki sources, accurate About metadata | Codex | 2-4k | Prepared; publication pending | Codex |
| M11 | Regression verification | Existing unit baseline; new local tests; lint/format; actual CI recorded | Codex | 1-3k | Local tests pass; final CI pending | Codex |
| M12 | Publish authorized batch | Canonical main updated without force; wiki/About verified; source remains intact | Codex | 1-2k | Pending | Codex |

## Boundaries and remaining learning

Read-only simulated furnace, no physical hardware or actuation. Custom information model, no certification/companion specification claim. No atomic cross-node snapshot, durable backlog, lossless delivery or production security claim. Unsecured UA restricted to loopback. Docker unavailable locally: remote stack acceptance must reference an actual successful CI result, not a configuration inspection.

Source quality, freshness and equipment state are separate. Legacy Modbus quality semantics remain as documented in B08; the new OPC UA adapter does not silently rewrite that baseline. The user still needs to explain the retained cases personally; this is not assessed by automated tests.

Next-step model recommendation: current Codex session for remaining batch verification/publication. Further security, physical PLC trials and user interview practice need separately scoped follow-up checkpoints.
