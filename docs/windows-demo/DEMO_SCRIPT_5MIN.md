# NEXUS — 5-Minute Demo Script

> **For live recruiter / hiring manager calls.**
> Talking points are word-for-word. Use the [Point at] cues to direct screen-sharing.
> Tags: **[MES]** manufacturing IT · **[OT]** IIoT/PLC · **[PLAT]** platform/full-stack

---

## Before the call — 5-minute checklist

- [ ] `start-demo.bat` run, both browser tabs open and showing live data
- [ ] Two tabs pinned: `http://localhost:3000` (Grafana) · `http://localhost:8080` (NEXUS)
- [ ] Scenario is NORMAL (run `scenario-reset.bat` if unsure)
- [ ] Screen sharing ready (Grafana tab visible first)
- [ ] This doc open on a second monitor or phone — not on the shared screen

---

## Intro — 30 seconds (no screen share yet)

> "Before I share my screen, let me frame what you're about to see in one sentence.
> This is a working factory monitoring system — Modbus PLCs on one end, a live decision dashboard on the other — built end-to-end by one engineer, running on my laptop right now."

*Now share screen with Grafana tab visible.*

---

## Screen 1 — Grafana Decision Board (60 s)

**URL:** `http://localhost:3000` → Aluminium Profile Decision Board

**[Point at]** The top banner (GREEN / line health)

> "This is the first thing a plant manager opens in the morning. One number — is the line healthy or not. Right now it's GREEN: all seven stations running normally. Furnace loading billets, press extruding, quench cooling profiles, stretcher straightening, saw cutting, ageing oven tempering. That's a complete aluminium extrusion sequence."

**[Point at]** Individual station tiles

> "Each tile is a live Modbus register read — temperature, flow rate, motor load, fault code — published over MQTT, stored in TimescaleDB, and queried by Grafana every two seconds. No spreadsheet. No manual entry."

**[If asked — MES]** *"Where does this sit relative to SAP or an MES?"*
> "It's the OT-to-IT bridge. This platform generates the events and KPIs that a proper MES or ERP would consume. Think of it as the shopfloor historian + alerting layer that sits below SAP PP or Wonderware."

**[If asked — OT]** *"What protocol is the simulator using?"*
> "Modbus TCP on port 1502 — same wire protocol as the Schneider and Allen-Bradley gear I've worked with. The collector polls every second per asset, publishes to MQTT topics in ISA-95 hierarchy."

---

## Screen 2 — Trigger the fault (45 s)

*Without leaving screen share, run `scenario-quench-fault.bat` from Explorer or say:*
> "I'm going to inject a live fault now — watch the board."

*Wait 10 seconds.*

**[Point at]** Banner flipping to AMBER + quench tile turning red

> "Quench flow just dropped below spec. Exit temperature is rising above the T5/T6 temper window. That's a quality hold on every aluminium profile that passed through the quench in the last few minutes — the Automotive Customer B order is at risk."

**[Point at]** The message in the decision tile

> "This message isn't a dashboard label I wrote by hand — it's generated dynamically from the alert state. The platform turns a raw Modbus fault code into a business-language action item."

**[If asked]** *"How fast does the alert fire?"*
> "Threshold layer fires within one collection cycle — one second after the register value crosses the rule. The statistical and ML layers fire within a few minutes as they build enough context."

---

## Screen 3 — NEXUS web app (60 s)

*Switch to `http://localhost:8080` tab.*

**[Point at]** Executive scenario banner at top

> "Same fault, different audience. This is the operations director view. The banner tells them what happened, which customer order is affected, and what action is recommended — all derived from the same telemetry stream."

*Navigate to `/alerts`*

**[Point at]** Open alert entry for QUENCH_FLOW_LOW

> "Every alert the engine generates lands here. Threshold rule, statistical deviation, ML anomaly — same inbox. Operators can acknowledge alerts and the acknowledge is stored; it's not just a UI state — it's a POST to the API, persisted in TimescaleDB, queryable in Grafana."

*Navigate to `/assets`, click quench-01*

**[Point at]** Signal history chart

> "Drill into the quench station — you can see the exact moment the flow dropped and temperature started climbing. This is the chart a maintenance engineer would use to write the incident report."

**[If asked — PLAT]** *"What's the frontend built in?"*
> "Svelte 5, compiled to vanilla JavaScript — no React, no heavy framework. The dashboard updates in real time via Server-Sent Events, which is a one-way HTTP stream from FastAPI. No WebSocket complexity."

---

## Screen 4 — Architecture (30 s)

*Navigate to [`docs/windows-demo/ARCHITECTURE_DIAGRAM.md`](./ARCHITECTURE_DIAGRAM.md) on GitHub, or open the local file.*

**[Point at]** Data flow diagram

> "Here's the full picture: Modbus device on the left, executive decision board on the right. Every hop is a deliberate technology choice documented in an Architecture Decision Record. I can walk through any layer — the Modbus register map, the MQTT topic schema, the TimescaleDB hypertable design, the ISA-95 naming convention, whatever is most relevant to the role."

**[If asked — MES]** *"Could this integrate with an existing MES?"*
> "Yes — two entry points. The FastAPI REST layer exposes KPIs and alerts with an API key; any MES with an HTTP client can pull or be pushed to via the webhook hook in the alert engine. ISA-95 topic hierarchy on MQTT means a plant historian like OSIsoft PI can subscribe natively."

---

## Screen 5 — Wrap + value statement (30 s)

*Stay on architecture diagram or return to Grafana GREEN state (run `scenario-reset.bat`)*

> "What this project demonstrates is that I can own the full vertical:
> the OT protocol layer, the messaging backbone, the data model, the alerting logic, the REST API, the frontend, and the infrastructure to deploy and operate all of it.
>
> In a manufacturing IT or IIoT role, that means I can sit in a room with a PLC engineer and a plant manager and an IT architect and speak all three languages without needing a translator."

**[Pause — let them ask.]**

---

## Reset after demo

Run `scenario-reset.bat` to return to NORMAL. Run `stop-demo.bat` when done.

---

## Stretch goals — 10-minute version

If they want to go deeper, pick from these:

1. **ADR walkthrough** — open `docs/adr/001-timescaledb-over-influxdb.md` and walk the decision: why not InfluxDB (no native JOINs at high cardinality), why not plain Postgres (no hypertable auto-compression). Shows architectural reasoning.

2. **MQTT topic schema** — open `contracts/` and show the ISA-95 hierarchy. Explain why `iiot/v1/telemetry/{site}/{line}/{asset}/{signal}` makes multi-site aggregation trivial.

3. **3-layer alert logic** — open `docs/adr/003-alert-three-layer.md`. Walk threshold → z-score baseline → IsolationForest. Ask them: "What does threshold alerting miss?" (drift). "What does statistical miss?" (novel pattern). ML fills that gap.

4. **Scale tiers** — show the Tier 1 / Tier 2 / Tier 3 table in README. "No code rewrites — only config." `docker compose up` → multi-site Compose overlay → Helm chart on Kubernetes.

5. **CI/CD** — open the GitHub repo Actions tab. Every push triggers lint + unit test + build. The badge on the README is live. Shows production-quality habits, not just a working demo.

---

## Likely recruiter questions — quick answers

| Question | Answer (one sentence + pointer) |
|---|---|
| "Is this production-ready?" | Demo-ready + architecturally production-shaped; gaps (TLS on MQTT, Vault secrets, load tests) are listed in `WINDOWS_DEMO.md` FAQ, not hidden. |
| "Why did you build this?" | To practise the OT/IT integration loop independently: simulated equipment, structured acquisition, monitoring and evidence-led assessment. |
| "What's the hardest part you built?" | The 3-layer alert deduplication: preventing duplicate alerts when all three detectors fire on the same signal simultaneously. See `services/alerting/`. |
| "Could you add OPC UA?" | The canonical NEXUS repository now includes a read-only local extension; use the current OPC UA guide/report to show exactly which paths were verified. |
| "What would you change first if this went to production?" | TLS on Mosquitto + mTLS for collector auth. Currently the MQTT ACL is username/password only; for a real factory VLAN that's acceptable but not ideal. |
| "Why Python and not Go?" | FastAPI + pydantic gives auto-generated OpenAPI docs and type-safe contracts for free; the performance ceiling for this data volume (1 sample/s per asset, 7 assets) is nowhere near the point where Go's throughput matters. |
| "Have you deployed this to cloud?" | Not yet — intentionally self-contained (no cloud dependency by design). The Helm chart is ready for a K8s cluster (EKS, AKS, GKE) when the use case justifies it. |
| "How long did this take?" | ~7 months of evenings and weekends (Sept 2025 → Apr 2026), building clean from scratch around a defined architecture. |
| "What's your weakest area in this stack?" | Honestly — the ML layer. IsolationForest is well-understood and explainable, but I'd want a data scientist to validate the feature engineering for a real production rollout. I built the pipeline; I'd collaborate on the model. |
| "What comes next?" | Real PLC connection trial, proper secret management (Vault), and a multi-tenant Tier 2 deployment across two simulated sites. See `PROGRESS.md`. |
