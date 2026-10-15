# OPC UA extension: know-how and how-to

Updated 15 October 2026. Canonical project: [NEXUS / IIoT-Telemetry-Stack](https://github.com/SaladinIART/IIoT-Telemetry-Stack). Python 3.13; tested optional library pin `asyncua==1.1.8`. All equipment inputs are independently invented and Simulated.

## What is actually connected?

The Python server exposes a fictional furnace. The client browses/reads/subscribes through the OPC UA binary protocol over loopback TCP. The optional MQTT sink publishes accepted observations using NEXUS's existing v2 payload and `iiot/v1/telemetry/{site}/{line}/{asset}/{signal}` topics. Existing consumers do not need to understand OPC UA.

OPC UA supplies an address space, typed values, status and timestamps. MQTT distributes mapped messages downstream. OPC UA client/server subscriptions and MQTT publish/subscribe are distinct; this case does not implement OPC UA PubSub.

## Install locally

From the repository root, with Python 3.13:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,opcua,opcua-test]"
```

On Linux/macOS use `source .venv/bin/activate`. `opcua-test` installs the isolated MQTT test broker; it is not a production broker dependency.

Terminal 1:

```sh
python -m iiot_stack.opcua_server --scenario normal
```

Terminal 2, same environment/root:

```sh
python -m iiot_stack.opcua_client --duration 12 --output tmp/normal-01.jsonl
```

Wait for the server's ready message before starting the client. Choose a new output filename for each run. The default output name, when omitted, contains a UTC timestamp. Stop with Ctrl+C. Both programs reject non-loopback endpoint addresses. Optional `--endpoint opc.tcp://127.0.0.1:4841/nexus/` must match between programs.

## Understand the address space

Namespace URI: `urn:salbotics:nexus:opcua:demo`. Browse `Objects -> NEXUS -> Furnace01`. The client resolves the numeric namespace index for the current session; it does not assume index 2.

| String NodeId (namespace resolved at runtime) | Type | Unit | Purpose |
| --- | --- | --- | --- |
| `furnace-01.billet_temp_c` | Double | degC | Existing furnace temperature signal |
| `furnace-01.preheat_zone_temp_c` | Double | degC | Existing preheat signal |
| `furnace-01.billet_loaded_count` | UInt32 | count | Existing counter |
| `furnace-01.state_code` | UInt16 | code | Existing equipment-state map |
| `furnace-01.fault_code` | UInt16 | code | Existing equipment fault |
| `furnace-01.acquisition_seq` | UInt64 | count | Independent acquisition progress indicator |

Each variable has a read-only custom `Unit` property. This deliberately small model does not claim AnalogItemType/EUInformation or an industry companion-specification implementation. Correctly typed client writes are rejected; server-internal updates drive the scenarios. Anonymous access is the only advertised identity token; remote admin escalation is disabled.

## Conduct the condition investigation

Restart Terminal 1 with one scenario at a time; collect to a new file in Terminal 2.

| Scenario argument | What happens | What to inspect |
| --- | --- | --- |
| `normal` | Temperatures vary deterministically | `browse`, `initial_read`, `connected`, `observation`, `telemetry` |
| `steady` | Constant temperature; acquisition sequence still advances | Old value SourceTimestamp, but no `acquisition_stale` |
| `frozen` | Acquisition stops after `--fault-after` seconds; server stays responsive | `acquisition_stale`; accepted telemetry stops |
| `bad` | Temperature status becomes BadSensorFailure | Null source value, raw status, `rejected`; no fabricated numeric point |
| `uncertain` | Temperature status becomes UncertainSensorNotAccurate | `rejected`; uncertain measurements not promoted to good |
| `process-fault` | State becomes FAULTED, fault 111, temperature 610 degC | Accepted Good-quality data can describe a real simulated fault |

Default acquisition interval: 1 second. Default subscription request: 500 ms. Default freshness timeout: 5 seconds. Default fault activation: 5 seconds after source start. Use at least 12 seconds to observe a default freeze and timeout. The retained study runner uses `--fault-after 2`, recorded in its source, so its 9-second freeze run includes the timeout.

To reproduce all six retained experiments:

```sh
python tools/run_opcua_study.py --output tmp/study-01
```

The output directory must not exist. Six real separate-process runs produce JSONL, process logs and a manifest with versions/source hashes. The normal/steady/frozen/quality/fault checks are assertions over observations, not prewritten success rows. Test reconnect separately:

```sh
pytest tests/integration/test_opcua_local.py -q
```

## Read the trace like an engineer

1. Confirm the `browse` record has the expected node/type/unit and no client write access.
2. Compare each `observation`'s status and source/server/receive timestamps.
3. Check acquisition sequence progress separately from temperature changes.
4. Locate a `rejected`, `acquisition_stale` or `transport_unavailable` record; explain why it does not necessarily mean an equipment fault.
5. Compare `telemetry` candidates with actual `mqtt_published` acknowledgments when bridging. A candidate alone is not broker delivery evidence.
6. Inspect the recorded recovery/gap. QoS 1 permits duplicates; this implementation has bounded queues, no durable backlog and no lossless guarantee.

DataValue status/timestamps follow [OPC Foundation Part 4](https://reference.opcfoundation.org/specs/OPC-10000-4/7.11). An unchanged value can keep its original SourceTimestamp. Neither its age nor a subscription keepalive alone establishes acquisition failure. Here acquisition sequence is the explicit teaching assumption. Callback receive monotonic time prevents old queued notifications being treated as newly received progress. No atomic multi-node snapshot is claimed.

The adapter rejects Bad/Uncertain, non-finite values, wrong types, unknown state codes and invalid source timestamps. Required state/fault metadata must be valid for this connection. It suppresses an unsuitable snapshot instead of emitting zero or silently stamping 'now'. Raw OPC UA metadata remains in diagnostic JSONL because the v2 schema forbids additional fields.

## Bridge to an existing local MQTT broker

Run only one publisher for `furnace-01`. Stop NEXUS's default Modbus collector before using the host OPC UA client against that broker. For a broker exposed on localhost:

```powershell
$env:MQTT_HOST = '127.0.0.1'
python -m iiot_stack.opcua_client --duration 20 --mqtt --output tmp/mqtt-01.jsonl
```

`MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`, `SITE` and `LINE` use the existing settings. Set real credentials in your environment, never in tracked files. Defaults match the repository's intentionally local demo profile. The client does not read `.env` automatically. `MQTT_HOST=mosquitto` resolves inside Compose, not normally from a host terminal.

For a hardware-free real MQTT test, with no Docker:

```sh
pytest tests/integration/test_opcua_mqtt.py -q
```

This starts an isolated loopback-only test broker, validates received topics/payloads, stops the broker, observes failed publication, restarts it and checks acknowledgment after recovery. It does not test database ingestion.

## Optional full NEXUS stack

```sh
docker compose -f docker-compose.yml -f docker-compose.opcua.yml config
docker compose -f docker-compose.yml -f docker-compose.opcua.yml up -d --build
python tools/verify_opcua_stack.py --output tmp/stack-check-01
```

The overlay replaces the collector build/command; it leaves the Modbus simulator present but its collector path inactive. The container runs separate server/client objects communicating over real loopback TCP. No UA port is published. JSONL persists in the `opcua_evidence` volume with a new file per start; do not erase that volume casually.

Grafana: `http://localhost:3000/d/nexus-opcua` (local-demo credentials in `.env.example`). Panels show last accepted temperature, delivery age and equipment state. Delivery age rises when accepted samples stop; it is not a specific root-cause alarm. Source timestamps may be old during healthy steady acquisition.

The verifier matches a PUBACK-confirmed candidate to an exact DB row, checks the API asset and queries the Grafana datasource for the same value. It does not assert pixel-level rendering or production suitability. CI runs this on an isolated runner; inspect its actual result/artifact before claiming success.

To return to Modbus:

```sh
docker compose -f docker-compose.yml -f docker-compose.opcua.yml down
docker compose up --build -d
```

No `-v`: preserve evidence volumes. Existing Compose reads service variables from `.env.example`; copying to `.env` affects Compose interpolation but does not replace those service `env_file` entries. Keep broker/database/Grafana credentials consistent if changing them. Production configuration requires a separate design.

## Troubleshooting and learning acceptance

- Connection refused: verify ready message, endpoint/port and that no prior server holds the port.
- Empty telemetry initially: readiness requires acquisition sequence progress after each connection; do not remove this guard to make a demo appear faster.
- `FileExistsError`: select a new output file/directory. Existing evidence is preserved intentionally.
- No MQTT acknowledgments: inspect broker host/auth and `mqtt_unavailable`; candidate records alone do not establish delivery.
- Missing optional library: install the `opcua` extra in the same interpreter used to launch the command.
- No Docker: use the local protocol tests; keep DB/API/Grafana runtime claims pending unless a real CI run succeeds.

Learner acceptance: explain a steady trace, a frozen trace and a process-fault trace; identify the raw evidence for each conclusion; change one scenario parameter and predict its effect before running it. Code tests do not assess this personal explanation.

Reference implementation: [FreeOpcUa asyncua](https://github.com/FreeOpcUa/opcua-asyncio). Monitored-item semantics: [OPC Foundation](https://reference.opcfoundation.org/specs/OPC-10000-4/5.13.1).
