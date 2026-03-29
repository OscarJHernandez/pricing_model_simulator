from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class PurchaseContext:
    """Per-evaluation context: temporal, geographic, and policy flags."""

    temporal_multiplier: float = 1.0
    geographic_multiplier: float = 1.0
    promo_eligible: bool = True
    is_weekend: bool = False


@dataclass
class Customer:
    """In-memory customer for simulation (maps to DB row after persist)."""

    customer_id: int  # DB pk when persisted
    customer_index: int
    budget: float
    buy_propensity: float
    price_threshold: float
    repeat_boost: float
    basket_mean: float
    location_zone: str
    acquisition_channel: str | None = None
    retention_sensitivity: float = 0.5
    promo_sensitivity: float = 0.5

    has_purchased_before: bool = False
    purchase_count: int = 0
    last_purchase_day: int | None = None
    assigned_treatment: str | None = None
    promo_uses_to_date: int = 0
    is_active: bool = True
    retention_score: float = 1.0

    last_promo_day: int | None = field(default=None, repr=False)

    def compute_purchase_probability(
        self,
        offered_price: float,
        current_day: int,
        context: PurchaseContext,
    ) -> float:
        if offered_price > self.budget:
            return 0.0

        base = self.buy_propensity
        # Price effect: softer when price is at/below threshold
        if self.price_threshold > 0:
            ratio = min(offered_price / self.price_threshold, 3.0)
            price_effect = 1.0 / (1.0 + max(0.0, ratio - 1.0))
        else:
            price_effect = 1.0

        if self.has_purchased_before:
            repeat_effect = 1.0 + self.repeat_boost * (1.0 + 0.1 * self.purchase_count)
        else:
            repeat_effect = max(0.15, 1.0 - 0.45 * self.promo_sensitivity)

        calendar = context.temporal_multiplier * context.geographic_multiplier
        if not context.promo_eligible:
            calendar *= 0.85

        retention = 1.0 + 0.15 * (self.retention_score - 1.0) * self.retention_sensitivity

        p = base * price_effect * repeat_effect * calendar * retention
        return float(np.clip(p, 0.0, 1.0))

    def decide_purchase(
        self,
        random_state: np.random.Generator,
        offered_price: float,
        current_day: int,
        context: PurchaseContext,
    ) -> bool:
        p = self.compute_purchase_probability(offered_price, current_day, context)
        return bool(random_state.random() < p)

    def register_purchase(self, current_day: int, order_value: float) -> None:
        self.has_purchased_before = True
        self.purchase_count += 1
        self.last_purchase_day = current_day
        self.retention_score = min(2.5, self.retention_score + 0.12 * self.retention_sensitivity)

    def decay_retention(self, days_since_purchase: int) -> None:
        if days_since_purchase <= 0:
            return
        decay = 0.01 * min(days_since_purchase, 30)
        self.retention_score = max(1.0, self.retention_score - decay)
