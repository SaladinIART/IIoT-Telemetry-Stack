"""Read-only, loopback-only OPC UA server with deterministic fictional inputs."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import math
from datetime import UTC, datetime

from asyncua import Server, ua

from iiot_stack.opcua_model import (
    ASSET,
    BROWSE_NAMES,
    ENDPOINT,
    NAMESPACE,
    NODE_TYPES,
    furnace_contract,
    loopback_endpoint,
    positive_seconds,
)

SCENARIOS = ("normal", "steady", "frozen", "bad", "uncertain", "process-fault")


class FurnaceServer:
    def __init__(self, endpoint=ENDPOINT, *, interval=1.0, scenario="normal", fault_after=5):
        self.endpoint = loopback_endpoint(endpoint)
        self.interval = positive_seconds(str(interval))
        if scenario not in SCENARIOS or not math.isfinite(fault_after) or fault_after < 0:
            raise ValueError("invalid scenario or fault_after")
        self.scenario = scenario
        self.fault_after = fault_after
        self.server = Server()
        self.nodes = {}
        self.previous = {}
        self.task = None
        self.sequence = 0

    async def __aenter__(self):
        await self.server.init()
        self.server.set_endpoint(self.endpoint)
        self.server.set_server_name("NEXUS fictional furnace — read-only teaching server")
        self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        self.server.iserver.allow_remote_admin = False
        self.server.set_identity_tokens([ua.AnonymousIdentityToken])
        index = await self.server.register_namespace(NAMESPACE)
        root = await self.server.nodes.objects.add_object(
            ua.NodeId("nexus", index), ua.QualifiedName("NEXUS", index)
        )
        asset = await root.add_object(ua.NodeId(ASSET, index), ua.QualifiedName("Furnace01", index))
        units = {s["tag_id"]: s["unit"] for s in furnace_contract()["signals"]}
        for tag, datatype in NODE_TYPES.items():
            node = await asset.add_variable(
                ua.NodeId(f"{ASSET}.{tag}", index),
                ua.QualifiedName(BROWSE_NAMES[tag], index),
                0,
                varianttype=datatype,
            )
            # Variables default to read-only for clients. Never call set_writable().
            await node.add_property(
                ua.NodeId(f"{ASSET}.{tag}.Unit", index),
                ua.QualifiedName("Unit", index),
                units.get(tag, "count"),
            )
            self.nodes[tag] = node
        self.started = asyncio.get_running_loop().time()
        await self.tick()
        await self.server.start()
        self.task = asyncio.create_task(self._acquire())
        return self

    async def __aexit__(self, *exc):
        if self.task is not None:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        await self.server.stop()

    async def _acquire(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.tick()

    async def tick(self):
        active = asyncio.get_running_loop().time() - self.started >= self.fault_after
        if active and self.scenario == "frozen":
            return  # Server stays responsive, but the source stops acquiring.
        self.sequence += 1
        angle = self.sequence * 0.2
        values = {
            "billet_temp_c": 570.0 if self.scenario == "steady" else 570 + 3 * math.sin(angle),
            "preheat_zone_temp_c": 550.0 if self.scenario == "steady" else 550 + math.cos(angle),
            "billet_loaded_count": 12 if self.scenario == "steady" else self.sequence // 5,
            "state_code": 3 if active and self.scenario == "process-fault" else 2,
            "fault_code": 111 if active and self.scenario == "process-fault" else 0,
            "acquisition_seq": self.sequence,
        }
        if active and self.scenario == "process-fault":
            values["billet_temp_c"] = 610.0
        now = datetime.now(UTC)
        for tag, value in values.items():
            code = ua.StatusCodes.Good
            if active and tag.endswith("temp_c"):
                if self.scenario == "bad":
                    code = ua.StatusCodes.BadSensorFailure
                elif self.scenario == "uncertain":
                    code = ua.StatusCodes.UncertainSensorNotAccurate
            signature = (value, code)
            if signature == self.previous.get(tag):
                continue  # Unchanged values keep their original source timestamp.
            variant = ua.Variant(value, NODE_TYPES[tag])
            if ua.StatusCode(code).is_bad():
                variant = ua.Variant(None, ua.VariantType.Null)
            await self.nodes[tag].write_value(
                ua.DataValue(variant, ua.StatusCode(code), SourceTimestamp=now, ServerTimestamp=now)
            )
            self.previous[tag] = signature


async def serve(args):
    async with FurnaceServer(
        args.endpoint, interval=args.interval, scenario=args.scenario, fault_after=args.fault_after
    ):
        print(
            f"NEXUS OPC UA server ready: {args.endpoint}; simulated scenario={args.scenario}",
            flush=True,
        )
        if args.duration:
            await asyncio.sleep(args.duration)
        else:
            await asyncio.Event().wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=ENDPOINT, type=loopback_endpoint)
    parser.add_argument("--interval", default=1.0, type=positive_seconds)
    parser.add_argument("--scenario", choices=SCENARIOS, default="normal")
    parser.add_argument("--fault-after", type=float, default=5.0)
    parser.add_argument("--duration", type=positive_seconds)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
