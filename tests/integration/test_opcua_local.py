"""Real loopback OPC UA traffic. No Docker, physical equipment or cloud."""

from __future__ import annotations

import asyncio
import json
import socket

import pytest

pytest.importorskip("asyncua")
from asyncua import Client, ua

from iiot_stack.opcua_client import EvidenceLog, collect
from iiot_stack.opcua_model import NAMESPACE, NODE_TYPES
from iiot_stack.opcua_server import FurnaceServer


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.asyncio
async def test_browse_types_units_read_and_rejected_write():
    endpoint = f"opc.tcp://127.0.0.1:{free_port()}/nexus/"
    async with FurnaceServer(endpoint, interval=0.05):
        async with Client(endpoint) as client:
            ns = await client.get_namespace_index(NAMESPACE)
            for tag, datatype in NODE_TYPES.items():
                node = client.get_node(ua.NodeId(f"furnace-01.{tag}", ns))
                assert await node.read_data_type_as_variant_type() == datatype
                assert ua.AccessLevel.CurrentWrite not in await node.get_user_access_level()
                assert await (await node.get_child(f"{ns}:Unit")).read_value()
            node = client.get_node(ua.NodeId("furnace-01.billet_temp_c", ns))
            with pytest.raises(ua.UaStatusCodeError) as failure:
                await node.write_value(ua.Variant(-999.0, ua.VariantType.Double))
            assert failure.value.code == ua.StatusCodes.BadUserAccessDenied
            assert await node.read_value() != -999.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario", ["normal", "steady", "frozen", "bad", "uncertain", "process-fault"]
)
async def test_subscription_scenarios(tmp_path, scenario):
    endpoint = f"opc.tcp://127.0.0.1:{free_port()}/nexus/"
    path = tmp_path / f"{scenario}.jsonl"
    log = EvidenceLog(path)
    try:
        async with FurnaceServer(endpoint, interval=0.05, scenario=scenario, fault_after=0.25):
            await collect(endpoint, duration=1.1, timeout=0.2, publish_ms=40, log=log)
    finally:
        log.close()
    rows = records(path)
    assert any(r["kind"] == "connected" for r in rows)
    payloads = [r["payload"] for r in rows if r["kind"] == "telemetry"]
    assert payloads
    if scenario == "steady":
        temperatures = [p for p in payloads if p["signal"] == "billet_temp_c"]
        assert len(temperatures) >= 2
        assert len({p["source_ts"] for p in temperatures}) == 1
        assert not any(r["kind"] == "acquisition_stale" for r in rows)
    elif scenario == "frozen":
        assert any(r["kind"] == "acquisition_stale" for r in rows)
        stale_index = next(i for i, r in enumerate(rows) if r["kind"] == "acquisition_stale")
        assert not any(r["kind"] == "telemetry" for r in rows[stale_index:])
    elif scenario in {"bad", "uncertain"}:
        assert any(r["kind"] == "rejected" and "non_good_status" in r["reason"] for r in rows)
    elif scenario == "process-fault":
        assert any(p["state"] == "FAULTED" and p["quality"] == "good" for p in payloads)


@pytest.mark.asyncio
async def test_reconnect_after_server_restart(tmp_path):
    endpoint = f"opc.tcp://127.0.0.1:{free_port()}/nexus/"
    path = tmp_path / "reconnect.jsonl"
    log = EvidenceLog(path)
    task = None
    try:
        async with FurnaceServer(endpoint, interval=0.05):
            task = asyncio.create_task(
                collect(endpoint, duration=6, timeout=0.3, publish_ms=40, log=log, retry_delay=0.1)
            )
            await asyncio.sleep(0.7)
        await asyncio.sleep(0.3)
        async with FurnaceServer(endpoint, interval=0.05):
            await task
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        log.close()
    rows = records(path)
    assert any(r["kind"] == "transport_unavailable" for r in rows)
    assert len([r for r in rows if r["kind"] == "connected"]) >= 2
    assert any(r["kind"] == "telemetry" and r["connection"] >= 2 for r in rows)
