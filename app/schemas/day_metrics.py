"""Typed shape of per-day aggregate metrics stored as JSONB on daily aggregates."""

from __future__ import annotations

from typing import TypedDict


class DayMetrics(TypedDict):
    """Structured daily rollup metrics persisted on `DailyAggregateRow.metrics`."""

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
