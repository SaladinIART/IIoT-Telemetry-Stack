from __future__ import annotations

import logging
import math
import struct
import threading
import time

import scenario_api
import scenario_state
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartTcpServer

from iiot_stack.industrial import load_assets
from iiot_stack.logging_utils import configure_logging

LOG = logging.getLogger("modbus_sim")


def float_words(value: float) -> list[int]:
    packed = struct.pack(">f", value)
    return list(struct.unpack(">HH", packed))


def uint32_words(value: int) -> list[int]:
    return [(value >> 16) & 0xFFFF, value & 0xFFFF]


def uint16_words(value: int) -> list[int]:
    return [value & 0xFFFF]


def build_context() -> ModbusServerContext:
    # 256 holding registers — 7 assets × 20-word stride needs addresses 0..127; +headroom.
    block = ModbusSequentialDataBlock(0, [0] * 256)
    slave = ModbusSlaveContext(hr=block)
    return ModbusServerContext(slaves={1: slave}, single=False)


def serve() -> None:
    configure_logging()

    # Start scenario HTTP API on port 5001 (background thread)
    threading.Thread(target=scenario_api.run, daemon=True).start()
    LOG.info("scenario API started on :5001")

    context = build_context()
    store = context[1]
    start = time.time()
    assets = load_assets()

    # 90-second cycling scenario windows (used when no scenario lock is active).
    # Pattern per station: brief STARTUP → long RUNNING → short FAULT → RUNNING → brief MAINT → RUNNING.
    scenario_windows = {
        "furnace-01": [
            (0, 6, 1, 0),
            (6, 38, 2, 0),
            (38, 45, 3, 111),
            (45, 62, 2, 0),
            (62, 70, 4, 0),
            (70, 90, 2, 0),
        ],
        "press-01": [
            (0, 8, 1, 0),
            (8, 40, 2, 0),
            (40, 48, 3, 211),
            (48, 66, 2, 0),
            (66, 74, 4, 0),
            (74, 90, 2, 0),
        ],
        "quench-01": [
            (0, 5, 1, 0),
            (5, 42, 2, 0),
            (42, 48, 3, 311),
            (48, 68, 2, 0),
            (68, 90, 2, 0),
        ],
        "cooling-01": [(0, 4, 1, 0), (4, 44, 2, 0), (44, 50, 3, 411), (50, 90, 2, 0)],
        "stretcher-01": [
            (0, 7, 1, 0),
            (7, 36, 2, 0),
            (36, 44, 3, 511),
            (44, 60, 2, 0),
            (60, 68, 4, 0),
            (68, 90, 2, 0),
        ],
        "saw-01": [
            (0, 5, 1, 0),
            (5, 40, 2, 0),
            (40, 47, 3, 611),
            (47, 64, 2, 0),
            (64, 72, 4, 0),
            (72, 90, 2, 0),
        ],
        "ageing-01": [(0, 10, 1, 0), (10, 50, 2, 0), (50, 57, 3, 711), (57, 90, 2, 0)],
    }

    counters = {asset["asset_id"]: 0 for asset in assets}

    def cycling_state(asset_id: str, elapsed: float) -> tuple[int, int]:
        second = int(elapsed) % 90
        for start_second, end_second, state_code, fault_code in scenario_windows[asset_id]:
            if start_second <= second < end_second:
                return state_code, fault_code
        return 2, 0

    def analog_values(
        asset_id: str, elapsed: float, state_code: int, fault_code: int
    ) -> tuple[float, float]:
        """Produce (primary, secondary) analog values centred within the register_map warn band.

        Fault codes push signals out of spec in physically plausible directions.
        IDLE/MAINTENANCE collapse the values to near-zero or hold-temperature levels.
        """
        phase = elapsed / 5.0
        if asset_id == "furnace-01":
            # billet_temp_c (warn 540..600), preheat_zone_temp_c (warn 520..580)
            primary = 572.0 + math.sin(phase / 1.3) * 12.0
            secondary = 552.0 + math.cos(phase / 1.7) * 10.0
            if fault_code == 111:  # OVER_TEMPERATURE
                primary = 612.0 + math.sin(phase) * 3.0
                secondary = 592.0 + math.cos(phase) * 3.0
            elif fault_code == 112:  # UNDER_TEMPERATURE
                primary = 520.0
                secondary = 498.0
            elif fault_code == 113:  # BURNER_TRIP
                primary = 420.0
                secondary = 410.0
            if state_code in {0, 4}:
                primary = max(80.0, primary * 0.25)
                secondary = max(60.0, secondary * 0.25)
        elif asset_id == "press-01":
            # ram_force_kn (warn 1500..2400), exit_profile_temp_c (warn 480..530)
            primary = 1950.0 + math.sin(phase) * 180.0
            secondary = 505.0 + math.cos(phase / 1.5) * 10.0
            if fault_code == 211:  # EXTRUSION_OVERLOAD
                primary = 2480.0 + math.sin(phase) * 30.0
                secondary = 540.0
            elif fault_code == 212:  # BILLET_JAM
                primary = 2400.0
                secondary = 455.0
            elif fault_code == 219:  # PRESS_EMERGENCY_TRIP
                primary = 0.0
                secondary = 320.0  # residual die heat
            if state_code in {0, 4}:
                primary = 0.0
                secondary = 300.0
        elif asset_id == "quench-01":
            # quench_flow_lpm (warn 180..260), exit_temp_c (warn 35..80)
            primary = 220.0 + math.sin(phase / 1.4) * 18.0
            secondary = 58.0 + math.cos(phase / 1.9) * 12.0
            if fault_code == 311:  # QUENCH_FLOW_LOW — flagship: flow drops AND exit temp rises
                primary = 148.0 + math.sin(phase) * 5.0
                secondary = 94.0 + math.cos(phase / 2.0) * 3.0
            elif fault_code == 312:  # QUENCH_TEMP_HIGH — inlet water too warm
                primary = 200.0
                secondary = 88.0 + math.sin(phase) * 2.0
            if state_code in {0, 4}:
                primary = 30.0  # idle circulation
                secondary = 30.0
        elif asset_id == "cooling-01":
            # table_temp_c (warn 40..85), conveyor_speed_m_min (warn 4..12)
            primary = 62.0 + math.sin(phase / 1.6) * 10.0
            secondary = 8.0 + math.cos(phase / 2.1) * 2.0
            if fault_code == 411:  # COOLING_TABLE_HOT
                primary = 95.0 + math.sin(phase) * 2.0
                secondary = 3.2
            elif fault_code == 412:  # COOLING_AIR_FLOW_LOW
                primary = 88.0
                secondary = 7.5
            if state_code in {0, 4}:
                primary = 35.0
                secondary = 0.0
        elif asset_id == "stretcher-01":
            # stretch_force_kn (warn 120..240), stretch_pct (warn 0.8..2.2)
            primary = 175.0 + math.sin(phase / 1.2) * 30.0
            secondary = 1.4 + math.cos(phase / 2.0) * 0.4
            if fault_code == 511:  # STRETCH_SLIP
                primary = 85.0
                secondary = 0.5
            elif fault_code == 512:  # STRETCH_FORCE_HIGH
                primary = 258.0
                secondary = 2.5
            if state_code in {0, 4}:
                primary = 0.0
                secondary = 0.0
        elif asset_id == "saw-01":
            # blade_rpm (warn 2400..3200), cut_length_dev_mm (warn -5..+5)
            primary = 2800.0 + math.sin(phase / 1.5) * 150.0
            secondary = 0.0 + math.cos(phase / 2.3) * 1.5
            if fault_code == 611:  # BLADE_WEAR
                primary = 2250.0 + math.sin(phase) * 60.0
                secondary = 2.5
            elif fault_code == 612:  # CUT_LENGTH_DEVIATION
                primary = 2700.0
                secondary = 7.5
            if state_code in {0, 4}:
                primary = 0.0
                secondary = 0.0
        else:  # ageing-01
            # oven_temp_c (warn 170..195), oven_dwell_min (warn 460..500)
            primary = 182.0 + math.sin(phase / 1.8) * 6.0
            secondary = 480.0 + math.cos(phase / 2.5) * 8.0
            if fault_code == 711:  # AGE_TEMP_DEVIATION
                primary = 165.0 + math.sin(phase) * 2.0
                secondary = 478.0
            elif fault_code == 712:  # AGE_DWELL_SHORT
                primary = 185.0
                secondary = 430.0
            if state_code in {0, 4}:
                primary = 40.0
                secondary = 0.0
        return float(primary), float(secondary)

    def updater() -> None:
        while True:
            elapsed = time.time() - start
            cycle_snapshot: dict[str, dict[str, float | int]] = {}
            for asset in assets:
                asset_id = asset["asset_id"]
                base_address = asset["base_address"]

                # Check for active scenario lock; fall back to 90-second cycling
                override = scenario_state.get_override(asset_id)
                if override is not None:
                    state_code, fault_code = override
                else:
                    state_code, fault_code = cycling_state(asset_id, elapsed)

                primary, secondary = analog_values(asset_id, elapsed, state_code, fault_code)

                # One profile/billet/batch per second when running — demo-friendly monotonic counter.
                if state_code == 2:
                    increment = 1
                else:
                    increment = 0
                counters[asset_id] += increment

                store.setValues(3, base_address, float_words(primary))
                store.setValues(3, base_address + 2, float_words(secondary))
                store.setValues(3, base_address + 4, uint32_words(counters[asset_id]))
                store.setValues(3, base_address + 6, uint16_words(state_code))
                store.setValues(3, base_address + 7, uint16_words(fault_code))

                cycle_snapshot[asset_id] = {
                    "primary": round(primary, 2),
                    "secondary": round(secondary, 2),
                    "count": counters[asset_id],
                    "state_code": state_code,
                    "fault_code": fault_code,
                }

            LOG.info("updated line registers", extra={"event": cycle_snapshot})
            time.sleep(1.0)

    threading.Thread(target=updater, daemon=True).start()
    StartTcpServer(context, address=("0.0.0.0", 1502))


if __name__ == "__main__":
    serve()
