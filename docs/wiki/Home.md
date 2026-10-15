# NEXUS — Industrial Intelligence Platform

NEXUS lives in **[SaladinIART/IIoT-Telemetry-Stack](https://github.com/SaladinIART/IIoT-Telemetry-Stack)**. This is the canonical repository; the aluminium demo repository remains preserved as a historical reference.

A software learning platform connecting simulated equipment through Modbus TCP or read-only OPC UA to MQTT, with existing TimescaleDB, FastAPI and Grafana components.

## Start here

- [Quick start](https://github.com/SaladinIART/IIoT-Telemetry-Stack/wiki/Quick-Start)
- [Architecture and protocol roles](https://github.com/SaladinIART/IIoT-Telemetry-Stack/wiki/Architecture)
- [OPC UA condition-assessment case](https://github.com/SaladinIART/IIoT-Telemetry-Stack/wiki/OPC-UA-Study-Case)
- [Evidence and limitations](https://github.com/SaladinIART/IIoT-Telemetry-Stack/wiki/Evidence-and-Limitations)
- [Repository README](https://github.com/SaladinIART/IIoT-Telemetry-Stack#readme)

## Evidence boundary

Equipment inputs are **Simulated**. Local OPC UA and MQTT tests use real network protocol connections. Neither establishes physical commissioning, field measurements, production security or a calibrated digital twin. Check the dated repository evidence report for exactly what was run.

Wiki sources are maintained in `docs/wiki/` in the main repository. Current code instructions take precedence over historical screenshots/walkthroughs.
