from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RecommendedAction(BaseModel):
    urgency: str  # IMMEDIATE | URGENT | SOON | INFO
    owner: str  # MANAGEMENT | MAINTENANCE | LOGISTICS | PRODUCTION
    action: str


class FinancialSummary(BaseModel):
    cost_rate_myr_hr: float  # Total RM/hr currently accumulating across faulted assets
    cost_so_far_myr: float  # RM accumulated since faults started
    orders_at_risk_count: int
    orders_at_risk_value_myr: float


class ProductionStatus(BaseModel):
    throughput_pct: float  # 0–100 (% of target line_rate running)
    units_today: (
        int  # aged_batch_count from ageing-01 since shift start (end-of-line T6 completion proxy)
    )
    target_today: int  # from production_schedule
    faulted_machine_count: int


class MaintenanceStatus(BaseModel):
    machines_healthy: int
    machines_at_risk: int  # pm_risk = MEDIUM
    machines_faulted: int
    current_mttr_estimate_min: int | None


class OrderSummary(BaseModel):
    id: str
    customer: str
    quantity_ordered: int
    due_at: Any  # datetime string
    order_value_myr: float
    computed_status: str  # ON_TRACK | MONITORING | AT_RISK | DELAYED | FULFILLED


class LogisticsStatus(BaseModel):
    orders_on_track: int
    orders_monitoring: int
    orders_at_risk: int
    orders_delayed: int
    next_deadline_at: Any | None
    next_deadline_customer: str | None
    orders: list[OrderSummary]


class AssetSummaryForDashboard(BaseModel):
    asset: str
    display_name: str
    asset_type: str
    state: str
    fault_code: int
    cost_rate_myr_hr: float
    cost_so_far_myr: float
    last_maint_at: Any | None
    pm_risk: str | None


class DashboardResponse(BaseModel):
    scenario: str  # NORMAL | QUALITY_HOLD_QUENCH | PRESS_BOTTLENECK | STRETCHER_BACKLOG | AGEING_OVEN_DEVIATION | EMERGENCY_PRESS_TRIP
    health: str  # GREEN | AMBER | RED | CRITICAL
    health_message: str
    financial: FinancialSummary
    recommended_actions: list[RecommendedAction]
    production: ProductionStatus
    maintenance: MaintenanceStatus
    logistics: LogisticsStatus
    assets: list[AssetSummaryForDashboard]
