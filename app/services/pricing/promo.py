"""Promo eligibility rules shared by the engine and future policy extensions."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.customer import Customer


@dataclass(frozen=True)
class PromoRules:
    """Caps and gates for applying variant discounts (campaign budget, per-customer use)."""

    first_order_only: bool = False
    max_uses_per_customer: int = 999
    cooldown_days: int = 0
    campaign_budget: float | None = None


def promo_eligible(
    customer: Customer,
    current_day: int,
    rules: PromoRules,
    cumulative_discount_spend: float,
) -> bool:
    """Return True if variant extra discount may apply for this customer on this day."""
    if rules.campaign_budget is not None and cumulative_discount_spend >= rules.campaign_budget:
        return False
    if rules.first_order_only and customer.purchase_count > 0:
        return False
    if customer.promo_uses_to_date >= rules.max_uses_per_customer:
        return False
    in_cooldown = (
        rules.cooldown_days > 0
        and customer.last_promo_day is not None
        and current_day - customer.last_promo_day < rules.cooldown_days
    )
    return not in_cooldown
