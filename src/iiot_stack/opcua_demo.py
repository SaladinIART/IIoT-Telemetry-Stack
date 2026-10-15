"""Container convenience: server and client communicate over real loopback OPC UA."""

from __future__ import annotations

import asyncio
import logging
import os

from iiot_stack.opcua_client import parser, run_args
from iiot_stack.opcua_server import FurnaceServer


async def run(args):
    async with FurnaceServer(args.endpoint, scenario=os.getenv("OPCUA_SCENARIO", "normal")):
        await run_args(args)


def main():
    args = parser().parse_args()
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
