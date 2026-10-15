# NEXUS — from factory-floor signals to decisions

[![CI](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/workflows/ci.yml/badge.svg)](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/workflows/ci.yml)

**A line goes into fault. Within seconds the system tells Quality, Maintenance and the shift supervisor what to do — and what it is costing.**

NEXUS connects a simulated seven-station aluminium extrusion line to a monitoring pipeline and turns equipment signals into prioritised actions, order risk and cost-of-downtime. It runs end to end on a laptop: Modbus (or OPC UA) → MQTT → TimescaleDB → alerting → API → dashboards.

### Try it

**[Open the live demo →](https://salbotics.uk/IIoT-Telemetry-Stack/)** — no install. Press *Quality Hold — Quench* in the control panel and watch the line go AMBER, alerts open and the recommended actions appear.

The hosted demo is a browser-only replay of API output recorded from the real stack (equipment is simulated). It shows a visible notice if the recording is a placeholder. To run the real pipeline yourself, see [Run it locally](#run-it-locally).

| Executive view | Decision board (Grafana) |
| --- | --- |
| ![Executive view](docs/windows-demo/screenshots/02-svelte-dashboard.png) | ![Grafana decision board with a quench fault](docs/windows-demo/screenshots/05-quench-fault-active.png) |

## What it shows

| Capability | How it appears in the project |
| --- | --- |
| Equipment to information | Seven stations, 35 signals, versioned JSON telemetry contract validated at publish and ingest |
| Decision support | Fault → recommended actions per owner, orders at risk, cost rate, quality-hold batches |
| Layered alerting | Threshold rules, statistical baseline and IsolationForest, de-duplicated into one alert stream ([ADR-003](docs/adr/003-alert-three-layer.md)) |
| Time-series design | TimescaleDB hypertables and views ([ADR-001](docs/adr/001-timescaledb-over-influxdb.md)) |
| Data reliability (OPC UA) | Separates *steady process* from *frozen acquisition*, *bad-quality source* and *lost connection* — with retained evidence |
| Engineering discipline | Contracts, ADRs, CI that traces one real payload through MQTT, database, API and Grafana |

## Architecture

```text
 Modbus simulator (7 stations) ──► collector ─┐
                                              ├─► MQTT (Mosquitto) ─► ingestor ─► TimescaleDB ─┬─► FastAPI + SSE ─► Svelte UI
 OPC UA furnace (optional) ──► client ────────┘                  └──► alerting ───────────────┘            └─► Grafana
```

Services are small and replaceable: `services/` (collector, ingestor, alerting, API), `sim/` (Modbus simulator and scenario API), `src/iiot_stack/` (shared contracts and OPC UA modules), `contracts/` (register map, topic and payload schemas), `db/migrations/`, `infra/` (Grafana provisioning, Mosquitto). Details: [architecture](docs/architecture.md).

## How this was built, with AI

I define the architecture, constraints and acceptance criteria; AI coding agents (Claude Code and Codex) do much of the implementation in small checkpoints, and nothing counts as done until it is verified.

- **Written plans first.** Work is split into checkpoints with explicit acceptance criteria ([example](docs/PORTFOLIO_DEMO_PLAN.md), [OPC UA consolidation plan](docs/opcua/CONSOLIDATION_PLAN.md)).
- **Evidence over assertion.** The OPC UA study retains raw JSONL traces with a hash manifest; CI runs a stack trace that matches an acknowledged payload to its database row and a Grafana query. Claims in the docs say what was and was not verified.
- **Guardrails.** Contracts and schemas are checked in tests, lint and format run in CI, and agent instructions live in the repo ([AGENTS.md](AGENTS.md)).
- **Honest scope.** Things that were never tested (a Helm chart, multi-site overlay) were removed instead of left as claims.

## Engineering depth: OPC UA condition assessment

The extension investigates one question: *when a temperature stops changing, is the process steady, acquisition frozen, the source unreliable, or the connection down?* A simulated furnace is exposed over read-only **OPC UA**; a client browses typed nodes, subscribes, and publishes approved samples to the same MQTT contract. Six scenarios (steady, frozen, bad, uncertain, process fault, normal) are run and retained.

- [Condition-assessment report](docs/opcua/CONDITION_ASSESSMENT.md) · [How-to and troubleshooting](docs/opcua/OPCUA_GUIDE.md) · [Study case](docs/opcua/U01_STUDY_CASE.md)

Try it without Docker (Python 3.13):

```sh
python -m venv .venv && . .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,opcua,opcua-test]"
python -m iiot_stack.opcua_server --scenario steady
# second terminal, same environment:
python -m iiot_stack.opcua_client --duration 12 --output tmp/my-first-opcua.jsonl
```

## Run it locally

```sh
docker compose up --build -d          # Modbus path
# or, with the OPC UA collector instead of the Modbus one:
docker compose -f docker-compose.yml -f docker-compose.opcua.yml up --build -d
```

- Web app: <http://localhost:8080> · API docs: <http://localhost:8080/docs> · Grafana: <http://localhost:3000>
- Scenarios are switched from the *Executive View* control panel or `docs/windows-demo/scripts/`.
- Credentials in `.env.example` are local-demo placeholders; see [SECURITY_PROFILE.md](SECURITY_PROFILE.md).

Build the browser demo (no backend) from recorded fixtures:

```sh
cd frontend && npm ci && BASE_PATH=/IIoT-Telemetry-Stack npm run build:demo
python tools/capture_demo_fixtures.py   # re-record fixtures from a running stack
```

## Verify

```sh
ruff check . && ruff format --check .
pytest tests/unit -q
pytest tests/integration/test_opcua_local.py tests/integration/test_opcua_mqtt.py -q
python tools/run_opcua_study.py --output tmp/my-opcua-study
```

Read the actual [Actions results](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions) as evidence of a passing run, not this description.

## Limitations

- Equipment inputs are **simulated**. Local OPC UA/MQTT tests use real loopback network traffic.
- Independent portfolio work: not employer data, not physical commissioning, not field measurements.
- Not a calibrated digital twin, and not a production-security qualification. The stack is a local demonstration profile.
- OPC UA is a client/server subscription demonstration (not PubSub), read-only, loopback only. No lossless-delivery or atomic multi-node snapshot guarantee is claimed.
- Only the single-host Docker Compose deployment is built and verified; the `site` dimension is in the schema, but a second site has not been exercised.

## Repository map

| Path | Purpose |
| --- | --- |
| `services/`, `sim/`, `src/iiot_stack/` | Pipeline services, simulator, shared contracts, OPC UA modules |
| `contracts/`, `db/migrations/` | Register map, topic/payload schemas, database schema and views |
| `infra/grafana/` | Provisioned dashboards (decision board, KPIs, OPC UA accepted-data health) |
| `frontend/` | Svelte UI, including the browser-only demo mode and its fixtures |
| `docs/` | Architecture, ADRs, runbooks, OPC UA study and evidence, wiki sources, archive |
| `tools/` | OPC UA study runner, stack verifier, demo fixture capture |

Built by [Muhamad Solehuddin](https://github.com/SaladinIART) — Salbotics.
