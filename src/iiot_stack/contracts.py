from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

# APP_ROOT lets Dockerfiles override the contracts location at runtime.
# In dev (editable install): __file__ is 3 levels up from repo root via src/iiot_stack/.
# When pip-installed: __file__ lands in site-packages — parents[2] is wrong,
# so containers must set APP_ROOT=/app.
ROOT = Path(os.environ.get("APP_ROOT", str(Path(__file__).resolve().parents[2])))
CONTRACTS_DIR = ROOT / "contracts"


@lru_cache(maxsize=1)
def load_register_map() -> dict[str, Any]:
    with (CONTRACTS_DIR / "register_map.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_payload_schema() -> dict[str, Any]:
    with (CONTRACTS_DIR / "telemetry_payload.schema.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def load_event_schema() -> dict[str, Any]:
    with (CONTRACTS_DIR / "event_payload.schema.json").open("r", encoding="utf-8") as handle:
        return json.load(handle)
