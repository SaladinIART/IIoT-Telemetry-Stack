"""B08 offline probe: what does the REAL collector publish for equipment
faults, transport failures, maintenance and frozen data?

It runs services/collector/app.py::run() unmodified, replacing only its
external edges (Modbus client, MQTT client, sleep/clock) with in-process
fakes. No network, broker, Docker, database or hardware is used, so this is
COMPONENT evidence for the collector only, not an end-to-end result.

Usage (project venv, from repository root):
    .venv/Scripts/python.exe docs/career-readiness/b08_collector_probe.py \
        --output docs/career-readiness/b08/collector_probe.json

The output path must not exist.
"""

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from iiot_stack.industrial import load_assets  # noqa: E402
import services.collector.app as collector  # noqa: E402


class StopProbe(BaseException):
    """BaseException so the collector's broad `except Exception` cannot swallow it."""


class FakeResult:
    def __init__(self, registers=None, error=False):
        self.registers = registers or []
        self._error = error

    def isError(self):  # noqa: N802 - mirrors pymodbus API
        return self._error


def _words(datatype, value):
    if datatype == "uint16":
        return [int(value) & 0xFFFF]
    if datatype == "uint32":
        v = int(value)
        return [(v >> 16) & 0xFFFF, v & 0xFFFF]
    if datatype == "float32":
        packed = struct.pack(">f", float(value))
        return list(struct.unpack(">HH", packed))
    raise ValueError(datatype)


class FakeModbus:
    """Serves a register image built from {asset_id: {tag_id: value}}."""

    image = {}
    connect_ok = True
    error_assets = set()

    def __init__(self, host, port=None, timeout=None):
        pass

    def connect(self):
        return type(self).connect_ok

    def read_holding_registers(self, address, count, slave):
        for asset in load_assets():
            if asset["unit_id"] != slave:
                continue
            for sig in asset["signals"]:
                if asset["base_address"] + sig["address_offset"] == address:
                    if asset["asset_id"] in type(self).error_assets:
                        return FakeResult(error=True)
                    value = type(self).image[asset["asset_id"]][sig["tag_id"]]
                    return FakeResult(_words(sig["datatype"], value))
        return FakeResult(error=True)


class FakeMqtt:
    def __init__(self):
        self.messages = []

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.messages.append((topic, json.loads(payload), retain))


class FakeTime:
    """Deterministic clock: sleep() advances time; stops after N sleeps."""

    def __init__(self, start, step_per_sleep, max_sleeps):
        self.now = start
        self.step = step_per_sleep
        self.left = max_sleeps

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.left -= 1
        self.now += self.step
        if self.left <= 0:
            raise StopProbe()


def normal_image():
    image = {}
    for asset in load_assets():
        image[asset["asset_id"]] = {
            s["tag_id"]: (2 if s["tag_id"] == "state_code" else 0)
            if s["signal_class"] in ("state", "fault") else 10.0
            for s in asset["signals"]
        }
    return image


def run_scenario(name, mutate, *, connect_ok=True, error_assets=(),
                 cycles=2, clock_step=1.0, freeze=False):
    assets = load_assets()
    image = normal_image()
    mutate(image)
    FakeModbus.image = image
    FakeModbus.connect_ok = connect_ok
    FakeModbus.error_assets = set(error_assets)
    mqtt = FakeMqtt()
    clock = FakeTime(1_800_000_000.0, clock_step, len(assets) * cycles)
    collector.connect_mqtt = lambda settings: mqtt
    collector.ModbusTcpClient = FakeModbus
    collector.configure_logging = lambda: None
    collector.time = clock
    try:
        collector.run()
    except StopProbe:
        pass
    rows = []
    for topic, p, retain in mqtt.messages:
        kind = "event" if "event_type" in p else "telemetry"
        rows.append({
            "topic": topic,
            "kind": kind,
            "asset": p.get("asset"),
            "state": p.get("state"),
            "fault_code": p.get("fault_code"),
            "quality": p.get("quality"),
            "event_type": p.get("event_type"),
            "reason_code": p.get("reason_code"),
            "source_ts": p.get("source_ts"),
            "ts": p.get("ts"),
        })
    return {"scenario": name, "messages": len(rows), "rows": rows}


def summarize(sc, asset=None):
    """Compact distinct (kind, state, fault_code, quality, event_type, reason)."""
    seen = []
    for r in sc["rows"]:
        if asset and r["asset"] != asset:
            continue
        key = (r["kind"], r["state"], r["fault_code"], r["quality"],
               r["event_type"], r["reason_code"])
        if key not in seen:
            seen.append(key)
    return [dict(zip(("kind", "state", "fault_code", "quality", "event_type",
                      "reason_code"), k)) for k in seen]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.output.exists():
        ap.exit(2, f"Refusing to overwrite {a.output}\n")

    first = load_assets()[0]["asset_id"]

    def fault(img):
        img[first]["state_code"] = 3
        img[first]["fault_code"] = 113

    def maintenance(img):
        img[first]["state_code"] = 4

    scenarios = [
        run_scenario("normal", lambda i: None),
        run_scenario("equipment_fault_burner_trip", fault),
        run_scenario("maintenance_state", maintenance),
        run_scenario("transport_modbus_connect_failed", lambda i: None,
                     connect_ok=False, cycles=1),
        run_scenario("transport_read_error_one_asset", lambda i: None,
                     error_assets=[load_assets()[1]["asset_id"]], cycles=1),
        # Source registers never change while the clock advances 5 minutes
        # per poll: the data are "frozen" but every value is re-stamped.
        run_scenario("frozen_source_values_clock_advances", lambda i: None,
                     cycles=3, clock_step=300.0),
    ]
    out = {
        "probe": "B08 collector component probe",
        "asset_under_test": first,
        "evidence_level": "Simulated component (real collector.run(), faked Modbus/MQTT/clock)",
        "not_covered": ["live Modbus", "MQTT broker", "ingestor/database", "API", "dashboard"],
        "scenarios": [],
    }
    for sc in scenarios:
        entry = {"scenario": sc["scenario"], "messages": sc["messages"],
                 "distinct_for_asset_under_test": summarize(sc, first),
                 "distinct_all_assets": summarize(sc)}
        if sc["scenario"].startswith("frozen"):
            tele = [r for r in sc["rows"] if r["asset"] == first and r["kind"] == "telemetry"]
            stamps = sorted({r["source_ts"] for r in tele if r["source_ts"] is not None})
            entry["distinct_source_ts_for_asset"] = len(stamps)
            entry["source_ts_span_seconds"] = (stamps[-1] - stamps[0]) / 1000.0 if stamps else None
        out["scenarios"].append(entry)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    with open(a.output, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"written {a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
