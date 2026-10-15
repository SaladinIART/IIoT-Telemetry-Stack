# NEXUS Portfolio Demo Plan

Goal: recruiters and clients visiting salbotics.uk/projects/nexus-iiot can **see NEXUS working in their browser in under 60 seconds**, then verify it is real (video + CI + clean repo).

## Decisions (agreed 2026-10-15)

| Topic | Decision |
| --- | --- |
| Demo format | Browser-only simulation + 60–90 s video of the real Docker stack |
| Sim UI | Reuse existing Svelte frontend; add demo-mode data layer (swap `api.ts` / `sse.ts` only). Unfreeze Svelte narrowly for this. |
| Data | Replay JSON captured from the **real** API, per scenario (6 scenarios), light jitter on live signals. No business-logic port. |
| Hosting | GitHub Pages from this repo → `https://salbotics.uk/IIoT-Telemetry-Stack/` (inherits user-site custom domain) |
| Narrative | Aluminium line decision-support first; OPC UA reliability study = "Engineering depth" section |
| Cleanup | Full: untrack build junk, archive internal docs, **delete** Helm + `docker-compose.multi.yml` + scaling runbooks 04/05, pin TimescaleDB |
| AI story | Dedicated "How I built it" section: human sets architecture + acceptance criteria, AI agents implement per checkpoint, CI + evidence gates |
| Video | User records + narrates; Claude writes 75 s shot list; unlisted YouTube embed |
| Website | Live site deploys from `SaladinIART.github.io` `origin/main` on push → changes via branch + PR |

## Tech-debt scores (Priority = (Impact + Risk) × (6 − Effort))

| Item | Score | CP |
| --- | --- | --- |
| Website links retired `salbotics-iiot-aluminium-demo` repo | 40 | CP-2 |
| 87 % of tracked files are build junk (`node_modules`, `.svelte-kit`, `static`, `tmp_*`) | 35 | CP-1 |
| README leads with OPC UA nuance; two competing stories | 32 | CP-8 |
| No zero-install demo | 30 | CP-5–CP-7 |
| Weak screenshots (all IDLE, 62 open alerts, empty throughput panel) | 28 | CP-9 |
| `timescaledb:latest-pg16` unpinned | 25 | CP-3 |
| Helm / multi-site (EMQX) drift, untested in CI | 20 | CP-3 |
| Docs sprawl (recovery, career-readiness, 50+ evidence logs) | 20 | CP-4 |
| Dev API key / default creds in bundle (label as demo-only) | 12 | CP-6 |

## Checkpoints

### CP-1: Untrack build artefacts
- Goal: Remove generated/temporary files from git so the repo opens clean.
- Acceptance criteria:
  - `git rm -r --cached` on `frontend/node_modules`, `frontend/.svelte-kit`, `services/api/static/_app`, `tmp_*.png`, `tmp_*.json`, `.claude/settings.local.json`, `Screenshots/` (move 2 useful shots to `docs/windows-demo/screenshots/` if not duplicates).
  - `.gitignore` covers `node_modules/`, `.svelte-kit/`, `services/api/static/`, `tmp_*`, `.claude/settings.local.json`.
  - API Dockerfile still builds frontend or documents `npm run build` step (check before untracking static).
  - `git ls-files | wc -l` < 300. `ruff check .` + `pytest tests/unit -q` pass.
- Recommended model: haiku-4-5 (low) — sonnet-4-6 if Dockerfile needs a frontend build stage
- Token estimate: ~20k (approx.)
- Status: done (2026-10-15, branch `chore/cp1-untrack-build-artefacts`, staged, not committed)
- Model used: opus-5-5 (low effort), ~35k tokens
- Notes: API image served the committed `static/`, so `services/api/Dockerfile` gained a `node:22-alpine` build stage + `.dockerignore`. Stage 1 reproduced locally from a clean copy (`npm ci && npm run build` → same 40 bundles, CRLF-only diffs); full `docker build` NOT run (no Docker in agent shell) — verify in CI or locally. Old `Screenshots/` showed a pre-v2 dashboard with nonsense values (e.g. Faulted Assets −8.15), so untracked rather than moved. Files remain on disk, now ignored.

### CP-2: Fix portfolio repo link (website quick win)
- Goal: Case-study "GitHub repository →" points at `SaladinIART/IIoT-Telemetry-Stack`.
- Acceptance criteria:
  - Branch off `origin/main` in `SaladinIART.github.io`; edit `src/data.js` (and `App.jsx` if hard-coded).
  - `npm run build` passes; PR opened, not merged without user OK.
- Recommended model: haiku-4-5 (low)
- Token estimate: ~10k (approx.)
- Status: done (2026-10-15) — PR SaladinIART/SaladinIART.github.io#5, branch `fix/nexus-repo-link`, worktree `Salbotics/salbotics-nexus-link-worktree` (main checkout had user-owned dirty edits, left untouched). Not merged.
- Model used: opus-5-5 (low effort), ~15k tokens

### CP-3: Delete unverified infra, pin images
- Goal: Repo claims only what CI verifies.
- Acceptance criteria:
  - Delete `helm/`, `docker-compose.multi.yml`, `docs/runbooks/04-scaling-to-tier2.md`, `05-scaling-to-tier3.md`.
  - `docs/architecture.md`, `PROGRESS.md`, README: no dangling references (`grep -ri "helm\|emqx\|multi.yml"` clean outside archive).
  - `timescale/timescaledb` pinned to an exact tag; `docker compose config` valid.
- Recommended model: haiku-4-5 (medium)
- Token estimate: ~20k (approx.)
- Status: done (2026-10-15, branch `chore/cp3-remove-unverified-infra`, stacked on CP-1 branch)
- Model used: opus-5-5 (edits) + sonnet-5-5 (verify, commit), ~50k tokens
- Notes: also rewrote the Tier 2/3 claims in architecture.md, ADR-002, WINDOWS_DEMO.md and DEMO_SCRIPT_5MIN.md (the demo script had recruiter talking points claiming a 'ready' Helm chart). PROGRESS.md and docs/recovery keep history with a removal note. TimescaleDB pinned to 2.30.2-pg16 = the digest `latest-pg16` resolved to on 2026-10-15 (6f139d56…), so runtime is unchanged. `docker compose config` NOT run (no Docker in agent shell); YAML parsed with Python instead.

### CP-4: Archive internal docs
- Goal: Top-level repo + `docs/` read like a product, not a work log.
- Acceptance criteria:
  - Move `docs/recovery/`, `docs/career-readiness/`, `PROGRESS.md`, `output/` → `docs/archive/` (keep `AGENTS.md` / `GEMINI.md` at root — agent tooling reads them there).
  - Keep one OPC UA evidence run (`2026-10-15-run-02`) + `release-verification`; archive the rest; update links in `docs/opcua/*.md`.
  - No broken relative links (scripted check).
- Recommended model: sonnet-4-6 (low)
- Token estimate: ~30k (approx.)
- Status: done (2026-10-15, branch `feat/portfolio-demo`)
- Model used: sonnet-5-5 (low), ~15k tokens
- Notes: deviated from plan: OPC UA evidence dirs NOT archived — every one is cited by the condition report (~700 KB total); moving them would break traceability. Archived recovery, career-readiness, PROGRESS.md, SWOT into docs/archive/ with README. Link check: 0 broken relative links.

### CP-5: Fixture capture script + real captures
- Goal: Record real API output for every scenario.
- Acceptance criteria:
  - `tools/capture_demo_fixtures.py`: for each of 6 scenarios → POST `/demo/scenario/{name}`, wait for pipeline settle, GET `/dashboard`, `/assets`, `/alerts`, `/kpis`, `/sites`, per-asset telemetry → `frontend/static/demo-fixtures/<scenario>/*.json` + `manifest.json` (capture time, git SHA, stack versions).
  - **User runs Docker stack once** (`docker` is not on PATH in Claude's shell); script runs end to end.
  - Fixtures < 2 MB total; no secrets.
- Recommended model: sonnet-4-6 (medium)
- Token estimate: ~40k (approx.)
- Status: partial — tooling done + tested; REAL capture still needs the user's Docker run
- Model used: sonnet-5-5 (medium), ~40k tokens
- Notes: `tools/capture_demo_fixtures.py` (tested against a stub API) writes real output + manifest `source: captured`. Because Docker is unavailable to the agent, `tools/make_placeholder_demo_fixtures.py` produces schema-validated PLACEHOLDER fixtures (`source: placeholder`, validated against the real Pydantic API schemas in tests) so CP-6+ can be built; the demo UI must show a visible notice while source != captured. To finish: `docker compose up --build -d` then `python tools/capture_demo_fixtures.py`, commit the result.

### CP-6: Svelte demo-mode data layer
- Goal: Frontend runs with no backend when `VITE_DEMO_MODE=true`.
- Acceptance criteria:
  - `src/lib/demo/` replays fixtures; `api.ts` and `sse.ts` branch on demo flag, no component changes beyond a "Browser replay of real NEXUS output — run the full stack with Docker" banner + link to repo.
  - Scenario buttons (DemoControlPanel) switch fixtures instantly; SSE emulated with timer + small jitter on numeric signals.
  - Acknowledge-alert works locally (in-memory).
  - `npm run build` (normal) unchanged; `npm run build:demo` outputs `frontend/build-demo/` with `paths.base = '/IIoT-Telemetry-Stack'`.
  - `AGENTS.md` updated: Svelte unfrozen for demo-mode only.
  - Manual browser check: all 6 scenarios, all routes, mobile width.
- Recommended model: sonnet-4-6 (high)
- Token estimate: ~80k (approx.)
- Status: todo
- Model used: —

### CP-7: GitHub Pages deploy
- Goal: Demo live at `https://salbotics.uk/IIoT-Telemetry-Stack/`.
- Acceptance criteria:
  - `.github/workflows/demo-pages.yml`: on push to main (paths `frontend/**`) → `npm ci && npm run build:demo` → deploy-pages.
  - Repo Pages source set to GitHub Actions (user does this in settings, or via `gh api` with OK).
  - Deep links and refresh work (404.html fallback).
- Recommended model: sonnet-4-6 (medium)
- Token estimate: ~30k (approx.)
- Status: todo
- Model used: —

### CP-8: README rewrite
- Goal: 10-second pitch for non-engineers, depth for engineers.
- Acceptance criteria:
  - Order: one-line pitch → **Live demo** button + video → what it shows (fault → actions + RM at risk) → architecture diagram → How I built it (AI-assisted, checkpoint + CI gates, one concrete example) → Engineering depth (OPC UA study) → run locally → limitations.
  - Under ~150 lines; all links valid.
- Recommended model: opus-4-7 (medium) — writing + positioning
- Token estimate: ~40k (approx.)
- Status: todo
- Model used: —

### CP-9: Fresh screenshots
- Goal: Screenshots show the strongest states.
- Acceptance criteria:
  - Captured from the live demo: Executive view (NORMAL GREEN), QUALITY_HOLD_QUENCH decision board, floor map with faulted station, KPI page, mobile view.
  - Replace `docs/windows-demo/screenshots/*`; captions state "simulated equipment".
- Recommended model: sonnet-4-6 (low)
- Token estimate: ~25k (approx.)
- Status: todo
- Model used: —

### CP-10: Video shot list
- Goal: User can record a 75 s video in one take.
- Acceptance criteria:
  - `docs/demo/VIDEO_SHOTLIST.md`: timed shots + narration lines (compose up → Grafana GREEN → inject quench → AMBER + actions → executive view → CI badge).
  - User records + uploads unlisted to YouTube; URL recorded.
- Recommended model: sonnet-4-6 (low)
- Token estimate: ~12k (approx.)
- Status: todo
- Model used: —

### CP-11: Website case-study upgrade
- Goal: salbotics.uk/projects/nexus-iiot shows output first.
- Acceptance criteria:
  - "Try the live demo" primary button + embedded video at top; new screenshots; "How I built it" section; OPC UA depth paragraph.
  - Branch off `origin/main`; `npm run build` passes; PR opened; preview checked at desktop + mobile.
- Recommended model: sonnet-4-6 (medium)
- Token estimate: ~60k (approx.)
- Status: todo
- Model used: —

## Model + token summary

| CP | Task | Recommended model | Token estimate (approx.) |
| --- | --- | --- | --- |
| CP-1 | Untrack build artefacts | haiku-4-5 | ~20k |
| CP-2 | Fix website repo link | haiku-4-5 | ~10k |
| CP-3 | Delete Helm/multi, pin images | haiku-4-5 | ~20k |
| CP-4 | Archive internal docs | sonnet-4-6 | ~30k |
| CP-5 | Fixture capture (needs Docker) | sonnet-4-6 | ~40k |
| CP-6 | Svelte demo-mode data layer | sonnet-4-6 | ~80k |
| CP-7 | GitHub Pages deploy | sonnet-4-6 | ~30k |
| CP-8 | README rewrite | opus-4-7 | ~40k |
| CP-9 | Fresh screenshots | sonnet-4-6 | ~25k |
| CP-10 | Video shot list | sonnet-4-6 | ~12k |
| CP-11 | Website case-study upgrade | sonnet-4-6 | ~60k |
| | **Total** | | **~367k** |
