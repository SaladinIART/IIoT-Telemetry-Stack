from __future__ import annotations

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status

from services.api.dependencies import get_conn, require_api_key
from services.api.schemas.asset import AssetStatus, AssetSummary

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

_LIST_SQL = """
SELECT asset, display_name, asset_type, site, line_name, cell_name,
       state, fault_code, quality, last_seen, open_alert_count
FROM v_asset_current_state
ORDER BY line_name, asset
"""

_GET_SQL = """
SELECT asset, display_name, asset_type, site, line_name, cell_name,
       state, fault_code, quality, last_seen, open_alert_count
FROM v_asset_current_state
WHERE asset = %s
"""


@router.get("", response_model=list[AssetSummary], dependencies=[Depends(require_api_key)])
def list_assets(conn: Annotated[psycopg.Connection, Depends(get_conn)]):
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(_LIST_SQL)
        return cur.fetchall()


@router.get("/{asset_id}", response_model=AssetSummary, dependencies=[Depends(require_api_key)])
def get_asset(asset_id: str, conn: Annotated[psycopg.Connection, Depends(get_conn)]):
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(_GET_SQL, (asset_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return row


@router.get(
    "/{asset_id}/status", response_model=AssetStatus, dependencies=[Depends(require_api_key)]
)
def get_asset_status(asset_id: str, conn: Annotated[psycopg.Connection, Depends(get_conn)]):
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(_GET_SQL, (asset_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return row
