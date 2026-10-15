from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, Query

from services.api.dependencies import get_conn, require_api_key
from services.api.schemas.telemetry import TelemetryPoint

router = APIRouter(prefix="/api/v1/assets", tags=["telemetry"])

_TELEMETRY_SQL = """
SELECT ts, asset, signal, value, quality, state
FROM telemetry
WHERE asset = %s
  AND (%s::text IS NULL OR signal = %s)
  AND ts >= %s
  AND ts <= %s
ORDER BY ts DESC
LIMIT %s
"""


@router.get(
    "/{asset_id}/telemetry",
    response_model=list[TelemetryPoint],
    dependencies=[Depends(require_api_key)],
)
def get_telemetry(
    asset_id: str,
    conn: Annotated[psycopg.Connection, Depends(get_conn)],
    signal: str | None = Query(None),
    from_ts: datetime = Query(
        default_factory=lambda: datetime(2000, 1, 1, tzinfo=UTC),
        alias="from",
    ),
    to_ts: datetime = Query(
        default_factory=lambda: datetime(2100, 1, 1, tzinfo=UTC),
        alias="to",
    ),
    limit: int = Query(500, ge=1, le=5000),
):
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(_TELEMETRY_SQL, (asset_id, signal, signal, from_ts, to_ts, limit))
        return cur.fetchall()
