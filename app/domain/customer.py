"""In-memory customer state and purchase context used by the simulation engine."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class PurchaseContext:
    """Context for a single purchase decision on one simulated day.

    Attributes:
        temporal_multiplier: Demand scaling from calendar effects (weekend, seasonality).
        geographic_multiplier: Zone-level demand modifier.
        promo_eligible: Whether variant promo rules allow a discount on this day.
        is_weekend: Whether the simulated day falls on a weekend (for downstream use).
    """

    temporal_multiplier: float = 1.0
    geographic_multiplier: float = 1.0
    promo_eligible: bool = True
    is_weekend: bool = False


@dataclass
class Customer:
    """Stochastic agent with budget, sensitivities, and evolving purchase history.

    ``customer_id`` is the database primary key after rows are flushed; it is ``-1`` while
    the cohort is only in memory.

    Attributes:
        customer_id: Primary key in ``customers`` once persisted.
        customer_index: Stable index within the simulated cohort (0-based).
        budget: Maximum total price the customer will consider paying.
        buy_propensity: Baseline purchase probability scale in (0, 1) space before modifiers.
        price_threshold: Soft reference price; offers above this reduce propensity.
        repeat_boost: Extra lift for repeat purchasers.
        basket_mean: Central tendency for lognormal basket draws.
        location_zone: Geographic bucket for multipliers and aggregation.
        acquisition_channel: Optional channel label for the synthetic cohort.
        retention_sensitivity: Weight on retention score in the purchase model.
        promo_sensitivity: Weight on first-order / promo-related dampening.
    """

    customer_id: int  # DB pk when persisted
    customer_index: int
    budget: float
    buy_propensity: float
    price_threshold: float
    repeat_boost: float
    basket_mean: float
    location_zone: str
    acquisition_channel: str | None = None
    channel_propensity_modifier: float = 1.0
    retention_sensitivity: float = 0.5
    promo_sensitivity: float = 0.5

    has_purchased_before: bool = False
    purchase_count: int = 0
    last_purchase_day: int | None = None
    assigned_treatment: str | None = None
    promo_uses_to_date: int = 0
    is_active: bool = True
    retention_score: float = 1.0
    cumulative_net_revenue: float = 0.0
    churned_day: int | None = None

    cumulative_contribution_margin: float = 0.0

    last_promo_day: int | None = field(default=None, repr=False)
    predicted_clv: float | None = field(default=None, repr=False)

    def compute_purchase_probability(
        self,
        offered_price: float,
        current_day: int,
        context: PurchaseContext,
    ) -> float:
        """Probability of purchase before RNG draw; clipped to [0, 1].

        Combines price vs threshold, repeat vs new behavior, calendar multipliers,
        and a mild retention score effect. ``current_day`` is reserved for future
        calendar logic; the model currently uses ``context`` and price only.
        """
        if offered_price > self.budget:
            return 0.0

        base = self.buy_propensity * self.channel_propensity_modifier
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
        """Bernoulli draw: returns True if uniform random draw is below probability."""
        p = self.compute_purchase_probability(offered_price, current_day, context)
        return bool(random_state.random() < p)

    def register_purchase(
        self, current_day: int, order_value: float, variable_cost: float = 0.0
    ) -> None:
        """Update counts, last purchase day, bump retention score, and accumulate revenue.

        ``variable_cost`` should be ``variable_cost_rate * basket`` so that
        ``cumulative_contribution_margin`` tracks actual margin rather than a post-hoc
        approximation derived from net revenue alone.
        """
        self.has_purchased_before = True
        self.purchase_count += 1
        self.last_purchase_day = current_day
        self.retention_score = min(2.5, self.retention_score + 0.12 * self.retention_sensitivity)
        self.cumulative_net_revenue += order_value
        self.cumulative_contribution_margin += order_value - variable_cost

    def decay_retention(self, days_since_purchase: int) -> None:
        """Gradually lower retention score when time passes since the last order."""
        if days_since_purchase <= 0:
            return
        decay = 0.01 * min(days_since_purchase, 30)
        self.retention_score = max(1.0, self.retention_score - decay)

    def compute_churn_probability(self, churn_base_rate: float) -> float:
        """Daily probability of churning, scaled by how far retention has decayed.

        At retention_score >= 2.0 churn probability is zero; at the floor (1.0) it equals
        churn_base_rate. Linear interpolation in between.
        """
        return float(np.clip(churn_base_rate * max(0.0, 2.0 - self.retention_score), 0.0, 1.0))

    def compute_predictive_clv(
        self,
        projected_days: int,
        discount_rate_annual: float,
        churn_base_rate: float,
        offered_price: float,
        current_day: int,
        context: PurchaseContext,
    ) -> float:
        """Expected discounted future revenue over ``projected_days`` using current state.

        Uses a finite geometric series that combines daily purchase probability,
        daily survival (inverse churn), and a per-day discount factor derived from
        the annual discount rate.  Churned customers return 0.

        ``offered_price`` should be the customer-specific expected basket total (e.g.
        ``customer.basket_mean + fees - discounts``), not a global config constant, so
        that the price-effect term in the probability formula reflects this customer's
        typical order size.
        """
        if not self.is_active:
            return 0.0
        p_buy = self.compute_purchase_probability(offered_price, current_day, context)
        daily_revenue = p_buy * self.basket_mean
        p_churn = self.compute_churn_probability(churn_base_rate)
        daily_discount = 1.0 - discount_rate_annual / 365.0
        s = (1.0 - p_churn) * daily_discount
        if s >= 1.0 or s <= 0.0:
            return daily_revenue * projected_days
        return float(daily_revenue * s * (1.0 - s**projected_days) / (1.0 - s))
