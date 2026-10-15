# Project instructions

## Repository identity

Canonical NEXUS repository: `SaladinIART/IIoT-Telemetry-Stack`. NEXUS is the project name. `salbotics-iiot-aluminium-demo` remains preserved as a historical source; new NEXUS work belongs here. Read `docs/opcua/CONSOLIDATION_PLAN.md` and `GEMINI.md` before continuing the OPC UA case. The 15 October 2026 consolidation/extension batch was implemented directly by Codex and is complete; older Claude/U01 dispatches are historical.

This project follows the global Codex workflow in `C:\Users\salbot01\.codex\AGENTS.md`.

> **Stack:** Preset **P3 — IIoT/OT Pipeline** — canonical NEXUS flagship. Canonical pins + conventions: [`..\STACK-STANDARD.md`](../STACK-STANDARD.md). Svelte frontend = frozen-legacy (do not expand) EXCEPT the browser-only demo mode (`VITE_DEMO_MODE`, `frontend/src/lib/demo/`, `npm run build:demo`) added for the salbotics.uk portfolio demo. Duplicate at `founder-hub\nexus-iiot-platform` is slated for retirement.

## Planning rules

Use `grill-me` and `caveman` for planning sessions.

Treat planning sessions as `gpt-5.4` with `high` reasoning.

Before activating any skill beyond `grill-me` and `caveman`, ask permission and mention the likely token usage impact.

Every substantial plan must include:

- dedicated checkpoints sized to project scope
- a master list inside each checkpoint so another model can resume immediately
- a recommended next-step model
- estimated token usage for each major task

For large projects, increase checkpoint count rather than combining too much work into one checkpoint.

## Gemini handoff

Use `GEMINI.md` in this project for language-oriented notes, writing context, terminology, summaries, and handoff details.
