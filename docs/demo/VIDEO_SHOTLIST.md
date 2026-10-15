# 75-second video: the real stack, fault to decision

Purpose: prove the live demo is not a mock-up. One take of the **real Docker
stack** going from healthy to a quality hold. Silent captions are fine; your
voice is better.

Target: 70–80 s · 1080p · screen recording of the browser only (no desktop,
no email, no tokens). Upload to YouTube as **Unlisted**, then give Claude the
URL for CP-11.

## One-time prep (also finishes the demo data)

Do this once in the same Docker session. It replaces the placeholder demo data
with output recorded from your real pipeline.

```powershell
docker compose up --build -d                        # or docs\windows-demo\scripts\start-demo.bat
python tools\capture_demo_fixtures.py               # ~3 min; records all 6 scenarios, ends on NORMAL
git add frontend\demo-fixtures; git commit -m "Capture real demo fixtures"
```

Then re-run `tools\capture_demo_screenshots.ps1` after rebuilding the demo so the
banner reads *captured*, not *placeholder*.

Before recording:

- [ ] Scenario is NORMAL (`docs\windows-demo\scripts\scenario-reset.bat`)
- [ ] Two tabs open and already signed in: Grafana `http://localhost:3000`
      (Aluminium Profile Decision Board) and NEXUS `http://localhost:8080/dashboard`.
      Sign in to Grafana **before** recording so the password never appears.
- [ ] Browser zoom 110–125 %, bookmarks bar hidden, notifications off
- [ ] Terminal ready with `docs\windows-demo\scripts\scenario-quench-fault.bat`
      (or send the scenario from the NEXUS control panel instead)

## Shot list

| # | Time | On screen | Say (or caption) |
| --- | --- | --- | --- |
| 1 | 0–8 s | Terminal: `docker compose ps`, all services *Up* | "This is NEXUS running locally: a Modbus simulator, MQTT, TimescaleDB, alerting, an API and two dashboards." |
| 2 | 8–20 s | Grafana decision board, health **GREEN** | "Seven stations of an aluminium extrusion line. Everything is healthy; the board is one number a plant manager reads in two seconds." |
| 3 | 20–28 s | Switch to the terminal, run `scenario-quench-fault.bat` | "Now I inject a fault: quench water flow drops below spec." |
| 4 | 28–45 s | Back to Grafana: board turns **AMBER**, quench tile red, decision table fills | "Within seconds the board flips. The system doesn't just say 'alarm' — it says who must do what: quality holds the batch, maintenance inspects the nozzles, logistics warns the customer." |
| 5 | 45–60 s | NEXUS `/dashboard`: banner, **cost rate**, **orders at risk**, actions | "The executive view translates the same fault into money and orders: cost per hour, and which customer order is at risk." |
| 6 | 60–68 s | `/alerts`: the open alert, click **Acknowledge** | "The alert streamed in without a refresh, and an operator can acknowledge it." |
| 7 | 68–75 s | Browser tab with the public demo `salbotics.uk/IIoT-Telemetry-Stack/` or the GitHub README | "Everything here is simulated equipment. You can try it yourself in the browser, and the code and evidence are on GitHub." |

## Do and don't

- **Do** say "simulated" once, clearly. The README and demo banner already do.
- **Don't** claim production deployment, customer data or certification.
- **Don't** show `.env`, API keys, or the Grafana login form.
- If the AMBER flip takes longer than ~15 s, cut the wait in editing rather than
  narrating over it.
- Re-run `scenario-reset.bat` afterwards (the scenario also auto-resets after
  10 minutes).

## After recording

1. Upload as **Unlisted**; title: *NEXUS: aluminium line fault to decision (simulated)*.
2. Description: link to the repo and `salbotics.uk/projects/nexus-iiot`.
3. Send the YouTube URL to Claude to embed in the case study (CP-11) and README.
