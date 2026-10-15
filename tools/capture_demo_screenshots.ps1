<#
.SYNOPSIS
  Capture reproducible screenshots of the browser demo with headless Edge/Chrome.

.DESCRIPTION
  Build first:  cd frontend; $env:BASE_PATH='/IIoT-Telemetry-Stack'; npm run build:demo
  Run:          powershell -File tools\capture_demo_screenshots.ps1
  Output:       docs\demo\screenshots\*.png

  Scenario states use the ?scenario= deep link. Re-run after
  tools\capture_demo_fixtures.py replaces the placeholder fixtures so the
  banner (and the pictures) reflect recorded pipeline output.
#>
param(
    [int]$Port = 4173,
    [string]$Out = (Join-Path $PSScriptRoot "..\docs\demo\screenshots")
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..")
$browser = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw "Edge or Chrome not found" }
if (-not (Test-Path "$repo\frontend\build-demo\404.html")) { throw "Run npm run build:demo first" }

New-Item -ItemType Directory -Force $Out | Out-Null
$Out = (Resolve-Path $Out).Path
$server = Start-Process -PassThru -WindowStyle Hidden python -ArgumentList "`"$repo\tools\serve_demo.py`"", "--port", $Port
Start-Sleep -Seconds 2

$base = "http://127.0.0.1:$Port/IIoT-Telemetry-Stack"
$shots = @(
    @{ name = "01-executive-normal";       path = "/dashboard?scenario=NORMAL";              size = "1440,900" },
    @{ name = "02-executive-quench-fault"; path = "/dashboard?scenario=QUALITY_HOLD_QUENCH"; size = "1440,1400" },
    @{ name = "03-floor-quench-fault";     path = "/?scenario=QUALITY_HOLD_QUENCH";          size = "1440,700" },
    @{ name = "04-alerts-quench-fault";    path = "/alerts?scenario=QUALITY_HOLD_QUENCH";    size = "1440,700" },
    @{ name = "05-executive-press-trip";   path = "/dashboard?scenario=EMERGENCY_PRESS_TRIP"; size = "1440,1400" },
    @{ name = "06-executive-narrow";       path = "/dashboard?scenario=QUALITY_HOLD_QUENCH"; size = "500,1500" }  # headless Chrome enforces ~500px min width
)
try {
    foreach ($s in $shots) {
        $file = Join-Path $Out "$($s.name).png"
        $browserArgs = @(
            "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=$($s.size)",
            "--virtual-time-budget=8000", "--screenshot=`"$file`"", "`"$base$($s.path)`""
        )
        Start-Process -FilePath $browser -ArgumentList $browserArgs -Wait -WindowStyle Hidden
        if (-not (Test-Path $file)) { throw "screenshot failed: $($s.name)" }
        Write-Host "captured $($s.name)"
    }
}
finally {
    Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
}
