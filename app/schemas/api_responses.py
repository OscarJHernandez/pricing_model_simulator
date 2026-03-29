"""Pydantic shapes for JSON returned by the runs API (OpenAPI + client contracts)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateRunResponse(BaseModel):
    """Acknowledgement after enqueueing a simulation."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: str


class RunSummary(BaseModel):
    """Short run metadata for list views."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    seed: int
    horizon_days: int
    customer_count: int
    created_at: str | None
    completed_at: str | None


class RunDetail(BaseModel):
    """Full run metadata including stored configuration snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    seed: int
    horizon_days: int
    baseline_end_day: int
    experiment_start_day: int
    customer_count: int
    error_message: str | None
    created_at: str | None
    completed_at: str | None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DayMetricsOut(BaseModel):
    """API view of `DayMetrics` (same keys as persisted JSONB)."""

    model_config = ConfigDict(extra="forbid")

    customers_evaluated: int
    orders: int
    conversion_rate: float
    average_order_value: float
    gross_revenue: float
    discount_spend: float
    net_revenue: float
    variable_cost: float
    contribution_margin: float
    orders_per_customer: float
    repeat_purchase_rate: float
    incremental_orders: int
    incremental_revenue: float
    incremental_margin: float
    non_incremental_discount_spend: float
    retained_customer_rate: float
    buyers_count: int
    repeat_buyers: int
    ever_purchased_before_day: int


class DailyAggregateOut(BaseModel):
    """One daily rollup row for a run."""

    model_config = ConfigDict(extra="forbid")

    day: int
    phase: str
    treatment: str | None
    location_zone: str | None
    metrics: DayMetricsOut


class CustomerOut(BaseModel):
    """Persisted customer draw exposed for inspection."""

    model_config = ConfigDict(extra="forbid")

    id: int
    customer_index: int
    budget: float
    buy_propensity: float
    price_threshold: float
    basket_mean: float
    location_zone: str


class TreatmentAssignmentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: int
    treatment: str


class OutcomeSampleOut(BaseModel):
    """Sparse outcome row for UI sampling."""

    model_config = ConfigDict(extra="forbid")

    day: int
    customer_id: int
    phase: str
    treatment: str | None
    purchased: bool
    incremental_order: bool
    net_revenue: float


class CustomerLTVOut(BaseModel):
    """Per-customer lifetime revenue summary for a completed run."""

    model_config = ConfigDict(extra="forbid")

    customer_id: int
    total_orders: int
    total_net_revenue: float
    total_contribution_margin: float
    days_active: int
    churned_day: int | None
    predicted_clv: float
    actual_clv_validation_revenue: float | None
