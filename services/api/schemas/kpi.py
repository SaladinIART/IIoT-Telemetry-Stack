from __future__ import annotations

from pydantic import BaseModel


class KpiSummary(BaseModel):
    asset: str
    display_name: str | None
    asset_type: str | None
    window_hours: float
    total_readings: int
    good_readings: int
    quality_rate: float  # 0.0 – 1.0
    running_minutes: float
    fault_minutes: float
    availability: float  # 0.0 – 1.0
    open_alert_count: int


class SiteSummary(BaseModel):
    site_id: str
    display_name: str
    location: str
    timezone: str
    active: bool
