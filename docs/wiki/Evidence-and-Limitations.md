# Evidence and limitations

Current local evidence (15 October 2026): six retained separate-process OPC UA scenarios; 60 passing local tests covering 35 existing unit cases, 16 new unit cases and nine OPC UA/MQTT integration cases. Tests include a real local MQTT broker and actual server/broker restart behavior.

The [condition report](https://github.com/SaladinIART/IIoT-Telemetry-Stack/blob/main/docs/opcua/CONDITION_ASSESSMENT.md) is authoritative for dated verification scope and CI acceptance. Its [manifests](https://github.com/SaladinIART/IIoT-Telemetry-Stack/tree/main/docs/opcua/evidence) record actual traces, source hashes and environment versions.

- Equipment inputs: **Simulated**, independently invented.
- Protocol exchange: real local OPC UA/MQTT, not physical commissioning.
- A candidate payload is not proof of MQTT delivery; a PUBACK is not proof of database insertion. The stack verifier checks these separately.
- A configured Compose file is not a successful run. Full-stack claims require the actual [Actions result](https://github.com/SaladinIART/IIoT-Telemetry-Stack/actions) and retained verification artifact.
- No atomic cross-node snapshot, lossless delivery, durable backlog, certified information model or production-security qualification.
- Unsecured UA is restricted to loopback. Physical PLC and certificate/trust trials are future separately scoped work.
- User explanation/independent competency remains NOT ASSESSED by code tests.

Historical screenshots and prior checkpoints remain as provenance. They do not prove that the current revision was rerun. New NEXUS work is canonical in this repository; the aluminium repository remains preserved.
