# Gemini Handoff

## Current — canonical NEXUS / OPC UA batch, 15 October 2026

- User explicitly authorized consolidation, direct Codex implementation and publication as one batch. Claude is not the implementer for this update.
- Canonical checkout: `C:/Users/salbot01/Salbotics/IIoT-Telemetry-Stack`; GitHub `SaladinIART/IIoT-Telemetry-Stack`. NEXUS is its project name. Aluminium repository/checkouts remain preserved.
- Read `docs/opcua/CONSOLIDATION_PLAN.md`, `OPCUA_GUIDE.md`, `CONDITION_ASSESSMENT.md` for current scope/status. Historical U01 dispatch is superseded for this batch.
- Source `99f4404` was an ancestor of imported `fb430f5`; history fast-forwarded on `codex/nexus-opcua-consolidation`. No new Svelte work. Existing Python lint/format cleanup only outside the new extension.
- Implemented typed read-only loopback server, browse/read/subscriptions, DataValue guards, acquisition-sequence freshness, reconnect and bounded MQTT bridge. Raw diagnostics stay separate from existing v2 schema. No physical data/commissioning, calibrated digital twin, production security or lossless/atomic-snapshot claim.
- COMPLETE: six retained separate-process experiments, 62 local tests, lint/format, and all three jobs of CI 38737854129 pass. Full stack trace verified on GitHub's Docker runner; local Docker unavailable. Original failed CI evidence/corrections retained; B08 probe reproduced unchanged.
- Wiki sources live in `docs/wiki/`; initialize wiki via browser once, then update its Git repository. About metadata should name NEXUS and OPC UA without production claims.
- Model used: Codex, exact variant unavailable. Actual token expenditure unavailable; checkpoint estimates are in the master list.
- README/About and five-page wiki published. Runtime tested at `a9cc81b55d7f15e651048fbb545d3bfb5f41a59c`; subsequent closeout changes are documentation/evidence only. Canonical U02-U10 functionality is covered by this completed batch; old one-CP Claude dispatch must not restart it. Stop; learner explanation/security/hardware are future separately authorized work.

## B08 review - 15 October 2026

B08 offline component baseline accepted: 35 tests and retained probe reproduced. See docs/career-readiness/b08/B08_REVIEW.md. End-to-end stack unverified; no source fix. User competency NOT ASSESSED.

## Current career-evidence checkpoint — 14 October 2026

The user approved retaining the existing aluminium scenario and understands the topic. CP-1 is a bounded baseline investigation before new fault-diagnosis functionality. Work is on `codex/equipment-fault-evidence` in a fresh C: clone; remote main and D: archive both matched `8e50fbc8e217fc0d149d601b14fec0cc6a507ff9`. Preserve D: as archive, including its untracked REINSTALL.md.

Read `docs/career-readiness/CP1_BASELINE.md` and `CP1_EVIDENCE.json` for acceptance status, environment, observations and limitations. Docker was unavailable in the checked environment, so a component/API probe cannot establish the complete pipeline. Existing public walkthrough claims also need review before promotion. No feature changes, push or publication. Stop after CP-1; obtain the user's continuation before CP-2. Exact session model and actual token usage are unavailable; model preference and estimates are recorded in the checkpoint report.

Use this file for language-oriented collaboration and cross-model continuity.

## Purpose

- Keep concise writing context for Gemini.
- Preserve terminology, tone, summaries, and open questions.
- Record checkpoint master lists so another model can continue cleanly.

## Checkpoint Template

### CP-01: Name

- Goal:
- Status:
- Scope:
- Dependencies:
- Recommended model:
- Estimated token usage:

Master list:
- Known facts
- Decisions made
- Files or areas involved
- Open questions
- Next exact action

## Language Notes

- Preferred tone:
- Domain terms:
- Phrases to avoid:

## Continuation Notes

- Current state:
- Risks:
- Next prompt for Gemini:

## B08 offline diagnostic baseline — 15 October 2026

- Claude Sonnet 5.5 (Claude Code), user-authorized batch. Added docs/career-readiness/b08_collector_probe.py and b08/ (collector_probe.json, B08_BASELINE.md). Real collector.run() with faked Modbus/MQTT/clock; no Docker/broker/frontend. 35 unit tests pass. Findings: equipment fault, maintenance and transport failure all surface as FAULTED with code 999 in the status event; "stale" quality = maintenance state; no data-age detection. No fixes made. READY_FOR_REVIEW.
