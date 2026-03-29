"""Build per-day aggregate metric dicts stored as JSON on daily aggregate rows."""

from __future__ import annotations

from app.schemas.day_metrics import DayMetrics


def empty_metrics() -> DayMetrics:
    """Return a metrics dict with numeric zeros suitable for mutation."""
    return {
        "customers_evaluated": 0,
        "orders": 0,
        "conversion_rate": 0.0,
        "average_order_value": 0.0,
        "gross_revenue": 0.0,
        "discount_spend": 0.0,
        "net_revenue": 0.0,
        "variable_cost": 0.0,
        "contribution_margin": 0.0,
        "orders_per_customer": 0.0,
        "repeat_purchase_rate": 0.0,
        "incremental_orders": 0,
        "incremental_revenue": 0.0,
        "incremental_margin": 0.0,
        "non_incremental_discount_spend": 0.0,
        "retained_customer_rate": 0.0,
        "buyers_count": 0,
        "repeat_buyers": 0,
        "ever_purchased_before_day": 0,
    }


def build_day_metrics(
    *,
    customers_evaluated: int,
    orders: int,
    gross_revenue: float,
    discount_spend: float,
    net_revenue: float,
    variable_cost: float,
    contribution_margin: float,
    buyers_today: int,
    repeat_buyers_today: int,
    customers_ever_purchased_before: int,
    incremental_orders: int,
    incremental_revenue: float,
    incremental_margin: float,
    non_incremental_discount_spend: float,
) -> DayMetrics:
    """Fill ratio and rate fields from raw counters for one aggregate bucket."""
    m = empty_metrics()
    m["customers_evaluated"] = customers_evaluated
    m["orders"] = orders
    m["gross_revenue"] = gross_revenue
    m["discount_spend"] = discount_spend
    m["net_revenue"] = net_revenue
    m["variable_cost"] = variable_cost
    m["contribution_margin"] = contribution_margin
    m["buyers_count"] = buyers_today
    m["repeat_buyers"] = repeat_buyers_today
    m["ever_purchased_before_day"] = customers_ever_purchased_before
    m["incremental_orders"] = incremental_orders
    m["incremental_revenue"] = incremental_revenue
    m["incremental_margin"] = incremental_margin
    m["non_incremental_discount_spend"] = non_incremental_discount_spend
    if customers_evaluated:
        m["conversion_rate"] = orders / customers_evaluated
    if orders:
        m["average_order_value"] = net_revenue / orders
    if customers_evaluated:
        m["orders_per_customer"] = orders / customers_evaluated
    if buyers_today:
        m["repeat_purchase_rate"] = repeat_buyers_today / buyers_today
    if customers_evaluated:
        m["retained_customer_rate"] = customers_ever_purchased_before / customers_evaluated
    return m
