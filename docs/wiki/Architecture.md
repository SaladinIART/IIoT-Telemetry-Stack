# Architecture and protocol roles

```text
Simulated Modbus line -> legacy Modbus collector --+
                                                   +-> MQTT -> ingestor -> TimescaleDB
Simulated furnace -> OPC UA server -> UA client ----+                          |
                                                                  API / Grafana
```

Select one collector path per asset/run. The optional OPC UA overlay replaces the existing collector rather than introducing a second furnace publisher.

- **OPC UA:** browse an address space, inspect types/units/access, read DataValues and subscribe to notifications. Namespace indexes are resolved by URI per session.
- **MQTT:** distribute accepted, schema-validated telemetry to existing NEXUS consumers.
- **TimescaleDB:** retain telemetry and support existing SQL views.
- **FastAPI/Grafana:** retrieve and present stored data. Grafana's OPC UA dashboard shows accepted-data age separately from equipment state.

This is OPC UA client/server subscription behavior, not OPC UA PubSub. MQTT topic hierarchy alone does not implement OPC UA discovery or information modeling.

Raw UA status and timestamps are retained in JSONL; telemetry v2 is unchanged. The new adapter rejects unsuitable snapshots and keeps equipment FAULTED state separate from source quality and connection loss. Legacy Modbus behavior remains as documented in the preserved B08 baseline.

Svelte remains frozen legacy; existing frontend work was imported without expansion. Scaling charts/configurations are historical design artifacts, not evidence of load qualification. See [current source](https://github.com/SaladinIART/IIoT-Telemetry-Stack/tree/main/src/iiot_stack) and [guide](https://github.com/SaladinIART/IIoT-Telemetry-Stack/blob/main/docs/opcua/OPCUA_GUIDE.md).
