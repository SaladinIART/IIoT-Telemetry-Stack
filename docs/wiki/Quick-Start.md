# Quick start

Use Python 3.13. Clone [the canonical repository](https://github.com/SaladinIART/IIoT-Telemetry-Stack), open its root, create/activate a virtual environment, then:

```sh
python -m pip install -e ".[dev,opcua,opcua-test]"
python -m iiot_stack.opcua_server --scenario steady
```

In another terminal using the same environment:

```sh
python -m iiot_stack.opcua_client --duration 12 --output tmp/steady-01.jsonl
```

Choose a new filename on subsequent runs. Expect browse/type/unit/access records, DataValue observations and accepted telemetry candidates. A steady value remains fresh while acquisition progresses. This client-only command does not run MQTT, TimescaleDB or Grafana.

Run six real separate-process experiments:

```sh
python tools/run_opcua_study.py --output tmp/study-01
```

Optional full stack, requiring Docker Compose:

```sh
docker compose -f docker-compose.yml -f docker-compose.opcua.yml up -d --build
python tools/verify_opcua_stack.py --output tmp/stack-check-01
```

The overlay replaces the Modbus collector, uses loopback OPC UA inside its container, and exposes no UA port. Grafana is at `http://localhost:3000`; FastAPI documentation at `http://localhost:8080/docs`. Review demo credentials and evidence-volume preservation in the [full guide](https://github.com/SaladinIART/IIoT-Telemetry-Stack/blob/main/docs/opcua/OPCUA_GUIDE.md). Do not connect demo defaults to real equipment.
