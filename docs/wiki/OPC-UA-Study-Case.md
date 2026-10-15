# OPC UA condition-assessment case

**Question:** a furnace temperature stops changing. Is the process steady, acquisition frozen, the source unreliable or the connection down?

The small custom model exposes five existing furnace signals plus an independent acquisition sequence. Inputs are fictional. Client/server traffic uses real local OPC UA.

| Experiment | Engineering distinction |
| --- | --- |
| Normal | Establish typed-read/subscription baseline |
| Steady | Old value timestamp can be valid while acquisition progresses |
| Frozen | Server alive does not prove source is acquiring |
| Bad / Uncertain | Do not promote unreliable data or invent zero |
| Process fault | FAULTED equipment can still have Good-quality measurements |
| Server restart | Re-establish subscription and readiness before resuming |
| Client write | Server must reject even a correctly typed write |
| MQTT outage | A telemetry candidate does not prove broker delivery |

Run the [guide](https://github.com/SaladinIART/IIoT-Telemetry-Stack/blob/main/docs/opcua/OPCUA_GUIDE.md), inspect [retained evidence](https://github.com/SaladinIART/IIoT-Telemetry-Stack/tree/main/docs/opcua/evidence), then read the [condition-assessment report](https://github.com/SaladinIART/IIoT-Telemetry-Stack/blob/main/docs/opcua/CONDITION_ASSESSMENT.md).

For each finding, identify the raw observation, alternative explanations and next check. Automated code tests do not establish personal mastery: explain three traces and predict a changed scenario before running it.

No physical condition, field measurements, predictive-maintenance accuracy or calibrated digital-twin claim follows from this software case.
