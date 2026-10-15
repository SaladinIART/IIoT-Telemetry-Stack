from __future__ import annotations

from typing import Annotated

import psycopg_pool
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from iiot_stack.settings import APISettings

_settings = APISettings()

# ── connection pool ───────────────────────────────────────────────────────────

_pool: psycopg_pool.ConnectionPool | None = None


def get_pool() -> psycopg_pool.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg_pool.ConnectionPool(
            conninfo=_settings.dsn,
            min_size=2,
            max_size=10,
            open=True,
        )
    return _pool


def get_conn(pool: Annotated[psycopg_pool.ConnectionPool, Depends(get_pool)]):
    with pool.connection() as conn:
        yield conn


# ── API key auth ──────────────────────────────────────────────────────────────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: Annotated[str | None, Security(_api_key_header)]) -> str:
    if key != _settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return key


# ── settings accessor ─────────────────────────────────────────────────────────


def get_settings() -> APISettings:
    return _settings
