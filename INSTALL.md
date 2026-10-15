# NEXUS IIoT Platform — Installation Guide

> **Current canonical project:** [IIoT-Telemetry-Stack](https://github.com/SaladinIART/IIoT-Telemetry-Stack). Start with the updated [README](README.md) or [OPC UA guide](docs/opcua/OPCUA_GUIDE.md). The guide below predates the OPC UA extension. Check the [condition report](docs/opcua/CONDITION_ASSESSMENT.md) for actual verification scope.

> **Who is this guide for?**
> This guide is written for anyone — engineers, managers, or students — who wants to run the NEXUS IIoT Platform on their own laptop or PC, even without prior experience in software development or Docker.
>
> By the end of this guide, you will have a fully working factory monitoring system running on your machine, complete with live sensor data, dashboards, and alerts.

---

## Table of Contents

1. [What You Are Installing](#1-what-you-are-installing)
2. [Minimum System Requirements](#2-minimum-system-requirements)
3. [Step 1 — Install Git](#step-1--install-git)
4. [Step 2 — Install Docker Desktop](#step-2--install-docker-desktop)
5. [Step 3 — Download the Project](#step-3--download-the-project)
6. [Step 4 — Start the Platform](#step-4--start-the-platform)
7. [Step 5 — Open the Interfaces](#step-5--open-the-interfaces)
8. [What You Should See](#what-you-should-see)
9. [How to Stop the Platform](#how-to-stop-the-platform)
10. [How to Restart After Rebooting](#how-to-restart-after-rebooting)
11. [Troubleshooting](#troubleshooting)
12. [Frequently Asked Questions](#frequently-asked-questions)

---

## 1. What You Are Installing

The NEXUS IIoT Platform is a **complete factory floor monitoring system** that simulates 4 industrial machines and shows their live data on dashboards.

Think of it like this:

```
[Simulated Factory Machines]
        Feeder, Mixer, Conveyor, Packer
              ↓  (sends data every 1 second)
        [NEXUS Platform on your PC]
              ↓
    ┌─────────────────────────────┐
    │  Grafana Dashboard :3000   │  ← Operator view (charts, trends)
    │  NEXUS Web App     :8080   │  ← Manager view (assets, alerts, KPIs)
    │  Database          :5432   │  ← All data stored here
    └─────────────────────────────┘
```

Everything runs **entirely on your machine** — no internet connection is needed after the initial download.

---

## 2. Minimum System Requirements

Before you start, make sure your computer meets these requirements:

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Operating System** | Windows 10 (64-bit), macOS 12, or Ubuntu 20.04 | Windows 11, macOS 14, Ubuntu 22.04 |
| **RAM (Memory)** | 4 GB | 8 GB or more |
| **CPU** | 2-core processor (Intel/AMD/Apple Silicon) | 4-core or more |
| **Free Disk Space** | 8 GB | 15 GB or more |
| **Internet Connection** | Required for first-time setup only | — |

> **How to check your RAM on Windows:**
> Press `Windows + R`, type `dxdiag`, press Enter. Look for "Memory" — it shows your total RAM.
>
> **How to check on Mac:**
> Click the Apple menu → About This Mac → look for "Memory".

---

## Step 1 — Install Git

Git is a tool that lets you download projects from the internet.

### Windows

1. Go to **https://git-scm.com/download/win**
2. Click the download button — it will automatically choose the right version for your PC
3. Run the downloaded installer (`.exe` file)
4. Click **Next** on every screen — the default settings are fine
5. Click **Install**, then **Finish**

### Mac

1. Open the **Terminal** app (search for "Terminal" in Spotlight)
2. Type this command and press Enter:
   ```
   xcode-select --install
   ```
3. A popup will appear — click **Install**
4. Wait for it to finish (this may take a few minutes)

### Linux (Ubuntu)

Open a terminal and run:
```bash
sudo apt update && sudo apt install -y git
```

### Verify Git is installed

Open a terminal (on Windows: search for "Command Prompt" or "PowerShell") and type:
```
git --version
```
You should see something like: `git version 2.43.0`

---

## Step 2 — Install Docker Desktop

Docker Desktop is the engine that runs all the platform components. It packages everything into isolated "containers" so nothing interferes with your existing software.

### Windows

1. Go to **https://www.docker.com/products/docker-desktop/**
2. Click **Download for Windows**
3. Run the downloaded installer (`Docker Desktop Installer.exe`)
4. When asked, make sure **"Use WSL 2"** is checked (recommended)
5. Click **OK** and wait for the installation to complete
6. **Restart your computer** when prompted
7. After restart, Docker Desktop will open automatically — wait for it to show **"Engine running"** (green circle in the bottom-left corner)

> **Windows users:** If you see an error about "WSL 2 kernel", follow the link in the error message to download and install the WSL 2 Linux kernel update, then restart Docker Desktop.

### Mac

1. Go to **https://www.docker.com/products/docker-desktop/**
2. Click **Download for Mac** — choose **Apple Silicon** if you have an M1/M2/M3/M4 chip, or **Intel** otherwise
   - Not sure which chip you have? Click Apple menu → About This Mac → look for "Chip" or "Processor"
3. Open the downloaded `.dmg` file
4. Drag **Docker** into your Applications folder
5. Open Docker from Applications
6. Follow the setup prompts — click **Accept** on the license agreement
7. Wait for the whale icon in the menu bar to stop animating — this means Docker is ready

### Linux (Ubuntu)

```bash
# Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and log back in, then verify:
docker --version
```

### Verify Docker is running

Open a terminal and type:
```
docker --version
```
You should see: `Docker version 27.x.x, build ...`

Then type:
```
docker compose version
```
You should see: `Docker Compose version v2.x.x`

If both commands work, Docker is ready.

---

## Step 3 — Download the Project

Now you will download the NEXUS platform to your computer.

1. Open a terminal:
   - **Windows:** Search for "PowerShell" in the Start menu and open it
   - **Mac/Linux:** Open the "Terminal" app

2. Choose a folder where you want to save the project. For example, your Desktop:
   ```bash
   # Windows PowerShell
   cd $HOME\Desktop

   # Mac / Linux
   cd ~/Desktop
   ```

3. Download (clone) the project:
   ```bash
   git clone https://github.com/SaladinIART/nexus-iiot-platform.git
   ```
   This will create a folder called `nexus-iiot-platform` on your Desktop.

4. Go into the project folder:
   ```bash
   cd nexus-iiot-platform
   ```

5. Copy the configuration file:
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env

   # Mac / Linux
   cp .env.example .env
   ```

> **What is the `.env` file?** It contains settings like passwords and port numbers for the platform. The default values work perfectly for a local demo — you don't need to change anything.

---

## Step 4 — Start the Platform

This is the main command that builds and starts everything. Run it from inside the `nexus-iiot-platform` folder:

```bash
docker compose up --build -d
```

**Breaking down this command:**
- `docker compose` — tells Docker to manage multiple containers together
- `up` — start everything
- `--build` — build the application code into Docker images first
- `-d` — run in the background (so your terminal stays usable)

**The first time you run this, it will:**
1. Download base images from the internet (~500 MB total)
2. Build the application code
3. Start 8 services in the correct order

**This takes 3–10 minutes on first run** depending on your internet speed. Subsequent starts take about 15 seconds.

You will see a lot of text scrolling by — this is normal. When it's done, you'll see your terminal prompt return.

### Check that everything started

```bash
docker compose ps
```

You should see all 8 services showing **"Up"** or **"running"**:

```
NAME               STATUS
iiot-alerting      Up
iiot-api           Up
iiot-collector     Up
iiot-grafana       Up
iiot-ingestor      Up
iiot-modbus-sim    Up
iiot-mosquitto     Up
iiot-timescaledb   Up
```

> If any service shows "Exit" or "Error", see the [Troubleshooting](#troubleshooting) section.

---

## Step 5 — Open the Interfaces

Wait about 30 seconds after Step 4 completes for all services to fully initialize, then open your web browser.

### Interface 1 — NEXUS Web Application (Manager View)

**URL:** http://localhost:8080

This is the main dashboard built for managers and engineers. You will see:
- **Floor Overview** — live cards for each machine showing its current state
- **Assets** — detailed view of each machine grouped by production line
- **Alerts** — list of triggered alerts with the ability to acknowledge them
- **KPIs** — availability and quality metrics per machine
- **Admin** — API key and site configuration

> **First time?** When you open the Admin page, you'll see an API Key field. The default key `nexus-dev-key-change-me` is already set. You can leave it as-is for testing.

### Interface 2 — Grafana Operator Dashboard (Technician View)

**URL:** http://localhost:3000

**Login credentials:**
- Username: `admin`
- Password: `change_me_now`

This is the classic industrial dashboard with time-series charts, showing:
- Healthy vs faulted assets
- Line output over time
- Asset state board
- Production and downtime KPIs

### Interface 3 — API Documentation (Developer View)

**URL:** http://localhost:8080/docs

This is an interactive API explorer (Swagger UI). You can click any endpoint and test it directly in the browser. Useful for developers who want to integrate with the platform.

---

## What You Should See

### NEXUS Web App (after ~30 seconds)

On the **Floor Overview** page (`http://localhost:8080`), you should see 4 asset cards:
- **Raw Material Feeder** — state: RUNNING, quality: good
- **Blend Mixer** — state: RUNNING, quality: good
- **Transfer Conveyor** — state: RUNNING, quality: good
- **Final Packer** — state: RUNNING, quality: good

Each card updates automatically every 2 seconds. The "last seen" time will keep changing.

### Grafana (after ~2 minutes of data collection)

On the **IIoT Telemetry Overview** dashboard, you will see:
- Live stat panels showing sensor values
- A rising line chart as data accumulates
- Asset state and alarm tables

If the charts show "No data", wait 1–2 minutes and refresh the page.

### Verify data is being stored

You can confirm data is flowing into the database by running this command in your terminal:

```bash
docker exec iiot-timescaledb psql -U iiot -d iiot -c "SELECT asset, signal, value, ts FROM telemetry ORDER BY ts DESC LIMIT 5;"
```

You should see 5 rows with recent timestamps.

---

## How to Stop the Platform

When you're done testing, stop all containers with:

```bash
docker compose down
```

This stops all 8 services but **keeps your data** — the database is preserved.

To stop AND delete all data (clean slate):
```bash
docker compose down -v
```

> The `-v` flag deletes all stored data. Only use this if you want to start completely fresh.

---

## How to Restart After Rebooting

If you restart your computer, Docker Desktop will start automatically on login (by default). Once Docker Desktop is running (green icon), open a terminal, go to the project folder, and run:

```bash
# Go to the project folder first
cd Desktop/nexus-iiot-platform    # Windows
cd ~/Desktop/nexus-iiot-platform  # Mac/Linux

# Start the platform (no --build needed this time — much faster)
docker compose up -d
```

The platform will be running in about 15 seconds.

---

## Troubleshooting

### "docker compose up" shows an error about a port being in use

This means another application is already using one of the required ports.

**Port 8080 in use:**
```bash
# Find what's using port 8080
# Windows PowerShell:
netstat -ano | findstr ":8080"

# Mac/Linux:
lsof -i :8080
```
If it's a web server or another application, stop it, then try again.

**Port 3000 in use:**
Grafana uses port 3000. If you have another app on port 3000, you can change Grafana's port by editing `docker-compose.yml` and changing `"3000:3000"` to `"3001:3000"`, then access Grafana at `http://localhost:3001`.

---

### Services show "Exit" or "Restarting" in docker compose ps

Get the error details:
```bash
# Replace <service-name> with the actual name (e.g., iiot-ingestor)
docker compose logs <service-name> --tail=20
```
Read the last few lines — the error message will tell you what went wrong.

Most common fix:
```bash
docker compose down
docker compose up -d
```
Wait 30 seconds, then check again.

---

### "No data" in Grafana

1. Wait 2 minutes after starting the platform — the first data takes a moment to arrive
2. Check the time range in Grafana — click the clock icon (top right) and select "Last 15 minutes"
3. Verify data is in the database:
   ```bash
   docker exec iiot-timescaledb psql -U iiot -d iiot -c "SELECT COUNT(*) FROM telemetry;"
   ```
   If the count is 0, check collector logs:
   ```bash
   docker compose logs collector --tail=20
   ```

---

### Floor Overview shows "No assets found"

The API may still be starting. Wait 30 seconds and refresh the page.

If it still shows no assets, check the API is running:
```bash
curl http://localhost:8080/health
```
Expected response: `{"status":"ok"}`

If you get "connection refused", the API container may have crashed:
```bash
docker compose logs api --tail=20
```

---

### "Docker Desktop is not running"

Open Docker Desktop from your Start menu (Windows) or Applications folder (Mac) and wait for the whale icon to stop animating (usually 30–60 seconds).

---

### Everything seems fine but Grafana says "Invalid username or password"

The default credentials are:
- Username: `admin`
- Password: `change_me_now`

If you changed the password and forgot it:
```bash
docker compose down -v
docker compose up -d
```
This resets everything including the Grafana password back to `change_me_now`.

---

## Frequently Asked Questions

**Q: Do I need to be connected to the internet to run this?**
Only for the first-time setup (to download Docker images and the project). After that, everything runs completely offline.

---

**Q: Is this safe to run on my work laptop?**
Yes. Everything runs inside isolated Docker containers — the platform cannot affect your other applications or files. It only uses network ports 8080, 3000, 5432, 1883, and 1502.

---

**Q: The simulator is generating fake data — can I connect real machines?**
Yes. The `services/collector/` service is designed to connect to real Modbus TCP devices. To connect real hardware, edit the `contracts/register_map.json` file with your device's IP address, port, and register addresses, then set the `MODBUS_HOST` environment variable to your device's IP address.

---

**Q: How much data does this generate?**
About 20–30 MB per day. The database is configured to automatically delete data older than 90 days.

---

**Q: Can I run this on a Raspberry Pi or small server?**
Yes, if it has at least 4 GB RAM and runs a 64-bit OS. The platform runs comfortably on an Intel NUC or similar mini-PC.

---

**Q: How do I update to a newer version?**
```bash
cd nexus-iiot-platform
git pull
docker compose down
docker compose up --build -d
```

---

**Q: I want to show this to my boss/team — what's the quickest demo path?**

1. Start the platform (`docker compose up -d`)
2. Open Grafana at `http://localhost:3000` — show the live telemetry charts
3. Open `http://localhost:8080` — show the floor overview updating in real-time
4. Open `http://localhost:8080/alerts` — this shows the alert inbox
5. Open `http://localhost:8080/docs` — this shows the full API explorer

The whole demo takes about 5 minutes and requires no explanation beyond "this is our live factory data, running on a single laptop."

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                  NEXUS IIoT Platform                        │
├──────────────────────┬──────────────────────────────────────┤
│  START               │  docker compose up -d                │
│  STOP                │  docker compose down                 │
│  STATUS              │  docker compose ps                   │
│  LOGS                │  docker compose logs <service>       │
│  RESET ALL DATA      │  docker compose down -v              │
├──────────────────────┼──────────────────────────────────────┤
│  Web App             │  http://localhost:8080               │
│  Grafana Dashboard   │  http://localhost:3000               │
│  API Docs (Swagger)  │  http://localhost:8080/docs          │
├──────────────────────┼──────────────────────────────────────┤
│  Grafana login       │  admin / change_me_now               │
│  API Key             │  nexus-dev-key-change-me             │
└──────────────────────┴──────────────────────────────────────┘
```

---

*Built by Salbotics Solutions, Penang*
*Questions or issues? Open a GitHub Issue at the project repository.*
