# CP-1 — Existing aluminium-demo baseline

Date: 14 October 2026. Local work only; no push, deployment or portfolio publication.

## Checkpoint master list

- **Goal:** Establish a trustworthy starting point for a fault-diagnosis case study while retaining the existing aluminium demonstration.
- **Acceptance criteria:** Compare archived/GitHub revisions; prepare an isolated working copy on C:; run available existing checks; attempt one existing fault/reset scenario; distinguish component evidence from full-pipeline evidence; preserve the archive and record blockers.
- **Recommended model:** Workspace preference is GPT-5.4 at high reasoning, if available. Availability and a model switch were not verified in this session.
- **Token estimate:** 4,000–7,000 for this bounded baseline inspection and report; estimate only.
- **Status:** Baseline investigation complete; component checks PASS, full-stack reproduction NOT RUN because the required runtime is unavailable.
- **Model used:** Current session model; exact model identity and measured token usage are unavailable to this report.

## Starting point

- Public remote: `https://github.com/SaladinIART/salbotics-iiot-aluminium-demo.git`.
- Remote `main` and archived HEAD both resolve to `8e50fbc8e217fc0d149d601b14fec0cc6a507ff9`.
- Archived checkout: `D:/Dev/automation/salbotics iiot stack`.
- Archive has one untracked `REINSTALL.md`; it was left in place and not copied into the new checkout.
- Fresh working clone: `C:/Users/salbot01/Salbotics/salbotics-iiot-aluminium-demo`.
- Working branch: `codex/equipment-fault-evidence`.
- Older `IIoT-Telemetry-Stack` checkout was not changed. Repository instructions identify it as the duplicate, not this project's development target.

## Environment and method

A project-local `.venv` was created using Python 3.13. Dependencies were installed using:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]' flask
```

Flask is required by the simulator API but is not declared in the root project dependencies. No global Python packages were changed. Package versions used for verification are recorded in the evidence JSON. The project's open-ended dependency ranges mean this environment is not an exact reconstruction of the historical April demonstration.

Docker was not found on PATH or in the checked standard Docker Desktop executable locations. The complete Modbus/MQTT/database/API/dashboard deployment therefore cannot yet be reproduced here. No Docker installation, system reconfiguration or existing service shutdown was attempted.

The narrower scenario probe uses Flask's in-process test client against the existing `scenario_api` routes, then inspects the existing scenario-state module. It covers normal state, the quench fault, an invalid request and explicit reset. It starts no listening server and does not exercise Modbus, MQTT, PostgreSQL, Grafana or the browser interface.

## Evidence

Machine-readable results: `CP1_EVIDENCE.json` in this directory. Existing unit tests are invoked with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q --junitxml=tmp/cp1-unit.xml
```

The evidence file records the exact scenario probe source, observations, source-file hashes, dependency versions and test output. Historical reports under `docs/recovery` remain historical; they are not substituted for a fresh full-stack result.

## Findings to resolve before expanding the project

1. **Transport health and equipment condition are coupled.** In `services/collector/app.py`, the `stale` quality value is assigned to a maintenance state. Failed collection publishes generic bad status as `FAULTED`. This supports investigating a clearer distinction between communication loss, measurement age and actual machine faults. It is a source observation, not a reproduced end-to-end stale-dashboard defect.
2. **Some relevant mechanisms already exist.** The project has fault scenarios, bad/stale sample handling, last-seen fields and reconnect/backoff behavior. A new feature should extend a demonstrated gap rather than duplicate these mechanisms.
3. **Public claims need an accuracy review.** The Windows walkthrough contains employer-derived framing, unverified readiness/performance/scalability claims and broad personal-ownership language. These conflict with the current independent-input and evidence-bounded portfolio direction. No private operational details are reproduced in this report. Do not promote the walkthrough unchanged; verify provenance and correct wording before publication work.
4. **The frontend is frozen legacy under repository instructions.** Any later display changes must respect that constraint; avoid a frontend expansion while proving the reliability behavior.

## Final assessment

| Acceptance item | Result |
| --- | --- |
| Compare archived/GitHub revisions | PASS — both match the recorded full commit SHA. |
| Prepare working copy on C: | PASS — fresh clone and dedicated local branch. |
| Run existing unit checks | PASS — 35 tests passed in 0.87 seconds, exit code 0. |
| Reproduce existing fault/reset at component level | PASS — scenario API gives NORMAL/GREEN, QUALITY_HOLD_QUENCH/AMBER with quench state/fault `(3, 311)`, and explicit reset restores all seven asset state tuples to `(2, 0)`. |
| Reject invalid scenario without changing active fault | PASS — HTTP 422, prior quench scenario preserved. |
| Reproduce full Modbus-to-dashboard pipeline | NOT RUN — Docker unavailable in the checked environment. |
| Preserve archive and original application code | PASS — archive retained; C: application code unchanged. Only checkpoint evidence and handoff documentation added/updated. |

Full-stack reproduction remains blocked by the unavailable Docker runtime in the checked environment. No component result proves a live alarm, dashboard refresh, database record or communication-recovery behavior. No hardware or production claim is made. The source observations above define candidates for investigation, not an implemented improvement.

## Continuation boundary

Stop after CP-1 reporting. Recommended next checkpoint outcome: a freshly reproduced full-stack NORMAL → QUALITY_HOLD_QUENCH → NORMAL sequence, once a suitable Docker runtime is available. Estimated 3,000–5,000 tokens excluding runtime installation/troubleshooting; use the workspace model preference above if available. Runtime changes need their own concrete scope if installation is required. Public-claim review remains a separate prerequisite to promoting the case study. No CP-2 implementation is authorized by this report. Measured CP-1 token usage is unavailable; the estimate must not be presented as actual usage.

RoboAQI continuity preflight reported stale/missing recent continuity state. Optional separate maintenance is `tools/Sync-RoboAQI.ps1 -Mode All` from the Salbotics workspace. It was not run; the D: archive was preserved.
