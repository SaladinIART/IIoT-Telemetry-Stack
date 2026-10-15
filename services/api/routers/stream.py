from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from services.api.dependencies import get_conn, require_api_key

LOG = logging.getLogger("api.stream")
router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

_LATEST_TELEMETRY_SQL = """
SELECT ts, asset, signal, value, quality, state
FROM telemetry
ORDER BY ts DESC
LIMIT 20
"""

_OPEN_ALERTS_SQL = """
SELECT id::text, opened_at, asset, signal, alert_type, severity, value, state, message
FROM alerts
WHERE state = 'OPEN'
ORDER BY opened_at DESC
LIMIT 20
"""


def _row_to_json(row: dict) -> str:
    return json.dumps(row, default=str)


async def _telemetry_generator(
    conn: psycopg.Connection,
) -> AsyncGenerator[str]:
    while True:
        try:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(_LATEST_TELEMETRY_SQL)
                rows = cur.fetchall()
            for row in rows:
                yield f"data: {_row_to_json(row)}\n\n"
        except Exception as exc:
            LOG.warning("SSE telemetry error", extra={"event": {"error": str(exc)}})
        await asyncio.sleep(2)


async def _alerts_generator(
    conn: psycopg.Connection,
) -> AsyncGenerator[str]:
    while True:
        try:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(_OPEN_ALERTS_SQL)
                rows = cur.fetchall()
            for row in rows:
                yield f"data: {_row_to_json(row)}\n\n"
        except Exception as exc:
            LOG.warning("SSE alerts error", extra={"event": {"error": str(exc)}})
        await asyncio.sleep(2)


@router.get("/telemetry", dependencies=[Depends(require_api_key)])
def stream_telemetry(conn: Annotated[psycopg.Connection, Depends(get_conn)]):
    return StreamingResponse(
        _telemetry_generator(conn),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/alerts", dependencies=[Depends(require_api_key)])
def stream_alerts(conn: Annotated[psycopg.Connection, Depends(get_conn)]):
    return StreamingResponse(
        _alerts_generator(conn),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
