# NEXUS — Industrial Intelligence Platform

**Canonical repository:** [SaladinIART/IIoT-Telemetry-Stack](https://github.com/SaladinIART/IIoT-Telemetry-Stack). NEXUS is the project name; IIoT-Telemetry-Stack is its repository name.

[![CI](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/workflows/ci.yml/badge.svg)](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions/workflows/ci.yml)
[Wiki](https://github.com/SaladinIART/IIoT-Telemetry-Stack/wiki) · [OPC UA guide](docs/opcua/OPCUA_GUIDE.md) · [Condition-assessment report](docs/opcua/CONDITION_ASSESSMENT.md) · [Consolidation record](docs/opcua/CONSOLIDATION_PLAN.md)

NEXUS connects simulated manufacturing equipment to a monitoring pipeline. Use **Modbus TCP** for register-based acquisition or the new **read-only OPC UA** path for browsable, typed data and subscriptions. Both feed the existing MQTT telemetry contract, TimescaleDB, FastAPI and Grafana.

The engineering question: **when a temperature stops changing, is the process steady, acquisition frozen, the source unreliable, or the connection down?** The OPC UA case investigates each possibility and retains its evidence.

## What this demonstrates

| Engineering skill | Practical example |
| --- | --- |
| OT/IT integration | Simulated furnace → OPC UA → MQTT → existing NEXUS consumers |
| Structured equipment data | Browse nodes, resolve namespace URI, inspect types/units/access |
| Data reliability | Separate source status, acquisition freshness and equipment state |
| Condition assessment | Compare baseline, steady, frozen, Bad/Uncertain and process-fault cases |
| Failure handling | Restore OPC UA subscriptions; expose MQTT delivery failure and gaps |
| Technical reporting | Reproducible commands, raw JSONL traces, hashes, conclusions and limitations |

**Evidence boundary:** equipment inputs are **Simulated**. Local OPC UA/MQTT tests use real loopback network traffic. This is independent portfolio work, not employer data, physical commissioning or field measurements. It is not a calibrated digital twin or a production-security qualification. Dated evidence and exact verification scope are in the [report](docs/opcua/CONDITION_ASSESSMENT.md).

## Try OPC UA without hardware or Docker

Requires Python 3.13. From a local clone:

```powershell
git clone https://github.com/SaladinIART/IIoT-Telemetry-Stack.git
cd IIoT-Telemetry-Stack
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,opcua,opcua-test]"
python -m iiot_stack.opcua_server --scenario steady
```

In a second terminal, activate the same environment, then:

```powershell
python -m iiot_stack.opcua_client --duration 12 --output tmp/my-first-opcua.jsonl
```

The client browses six nodes, reads full DataValues, subscribes and records approved telemetry candidates. A steady temperature remains healthy while acquisition sequence advances. Use `--scenario frozen`, `bad`, `uncertain` or `process-fault` on a new server run to investigate other conditions. Stop the previous server before starting another on the same port. Use a new output filename for each run: evidence is never silently overwritten.

The teaching endpoint is restricted to loopback. Client writes are rejected; no physical equipment is connected. This is an OPC UA client/server subscription demonstration, not OPC UA PubSub. See [how-to and troubleshooting](docs/opcua/OPCUA_GUIDE.md).

## Architecture

```text
Legacy path: seven-station fictional aluminium Modbus simulator
                  → existing Modbus collector ───────────────┐
                                                            ↓
Optional path: fictional furnace OPC UA server → client → MQTT
                                                            ↓
                               existing ingestor / alerting services
                                                            ↓
                                                   TimescaleDB
                                                            ↓
                                              FastAPI / Grafana
```

Select one collector path per asset/run. The OPC UA overlay replaces the default collector; it does not add a competing furnace publisher. Equipment state and data quality are independent: an over-temperature fault can have Good-quality measurements.

Raw OPC UA status/timestamps stay in diagnostic JSONL because existing telemetry v2 does not allow extra fields. Bad/Uncertain, malformed or stale observations are suppressed, rather than converted to zero or falsely labelled fresh. No atomic multi-node snapshot or lossless delivery guarantee is claimed.

## Existing stack and optional OPC UA mode

With Docker Compose available, the existing Modbus demonstration remains:

```sh
docker compose up --build -d
```

For the OPC UA collector instead:

```sh
docker compose -f docker-compose.yml -f docker-compose.opcua.yml up --build -d
```

- Grafana: `http://localhost:3000` — **NEXUS OPC UA — accepted-data health** dashboard.
- FastAPI: `http://localhost:8080/docs`.
- Existing Svelte views are retained as frozen legacy; no frontend expansion is part of this update.
- OPC UA server/client communicate over loopback inside the collector container. No unsecured OPC UA port is exposed.
- Example credentials are local-demo placeholders. The existing stack is not a production deployment profile; review [security notes](SECURITY_PROFILE.md).
- `docker-compose.opcua.yml` is opt-in. The client-only CLI does not start a broker or database.

To return to Modbus mode, stop the OPC UA configuration first, then start the base configuration. Keep evidence volumes unless you intentionally want to remove retained runs. Full instructions, environment configuration and verification commands are in the [guide](docs/opcua/OPCUA_GUIDE.md).

## Verify and reproduce

```sh
ruff check .
ruff format --check .
pytest tests/unit -q
pytest tests/integration/test_opcua_local.py tests/integration/test_opcua_mqtt.py -q
python tools/run_opcua_study.py --output tmp/my-opcua-study
```

The study runner launches separate server/client processes for six scenarios, retains actual observations and writes a hash manifest. It never generates pretend measured results. The local MQTT test starts an isolated, loopback-only test broker and verifies actual delivery/outage/recovery; it does not exercise TimescaleDB.

CI also runs `tools/verify_opcua_stack.py` against the OPC UA Compose configuration to match an acknowledged payload to its database row and Grafana data-source response, and check FastAPI. Read the actual [Actions result](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions), not this description, as evidence of a passing run. Historical screenshots are not proof that the current stack was rerun.

## Repository map

| Path | Purpose |
| --- | --- |
| `src/iiot_stack/opcua_*.py` | Model, simulated server, client, mapping/freshness and MQTT sink |
| `contracts/` | Existing equipment register map and telemetry/event schemas |
| `services/` | Existing Modbus collector, ingestion, alerting and API; optional OPC UA container |
| `infra/grafana/` | Existing dashboards plus OPC UA accepted-data health |
| `docs/opcua/` | Study plan, guide, condition report and retained experiments |
| `docs/wiki/` | Version-controlled sources for GitHub wiki pages |
| `docs/archive/` | Historical build log, recovery checkpoints and earlier baselines |
| `frontend/` | Frozen Svelte source and historical built assets |

## NEXUS consolidation

The original repository already contained NEXUS. Its `99f4404` history was an ancestor of the aluminium demo at `8e50fbc`; the later local diagnostic baseline was `fb430f5`. This update imports that descendant history and adds the OPC UA extension here. The [aluminium demo repository](https://github.com/SaladinIART/salbotics-iiot-aluminium-demo) remains preserved; new NEXUS work belongs here. No repository was deleted or force-pushed.

Built by [Muhamad Solehuddin](https://github.com/SaladinIART) — Salbotics Solutions.
