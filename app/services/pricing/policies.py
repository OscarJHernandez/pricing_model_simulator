"""Composable baseline and experiment-arm pricing for basket-level totals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExperimentTreatmentName = Literal["control", "variant"]


@dataclass(frozen=True)
class BaselinePolicy:
    """Pre-experiment list pricing: subtotal plus delivery and service, minus discounts.

    ``order_price`` is deprecated and unused — basket totals in the engine are always
    drawn from a per-customer lognormal distribution, not this fixed value.
    """

    delivery_fee: float
    service_fee: float
    discount_amount: float = 0.0
    free_delivery_threshold: float | None = None
    order_price: float = 0.0

    def total_customer_price(self, subtotal: float) -> float:
        """Customer total after free-delivery threshold and fixed discounts."""
        delivery = self.delivery_fee
        if self.free_delivery_threshold is not None and subtotal >= self.free_delivery_threshold:
            delivery = 0.0
        return subtotal + delivery + self.service_fee - self.discount_amount


@dataclass(frozen=True)
class ExperimentArm:
    """One experiment arm: delivery fee and optional extra discount on top of baseline."""

    name: ExperimentTreatmentName
    delivery_fee: float
    discount_amount: float = 0.0


@dataclass(frozen=True)
class PricingPolicy:
    """Baseline fees plus control/variant arms used after experiment start day."""

    baseline: BaselinePolicy
    control: ExperimentArm
    variant: ExperimentArm

    def arm_for_treatment(self, treatment: str | None) -> ExperimentArm:
        """Map API treatment label to arm; unknown or missing values use control."""
        if treatment == "variant":
            return self.variant
        return self.control

    def baseline_total(self, basket: float) -> float:
        """Total customer-paid price in the baseline phase for a basket subtotal."""
        return self.baseline.total_customer_price(basket)

    def experiment_total(self, basket: float, treatment: str | None) -> float:
        """Total price under experiment rules, reusing baseline service and thresholds."""
        arm = self.arm_for_treatment(treatment)
        base = BaselinePolicy(
            delivery_fee=arm.delivery_fee,
            service_fee=self.baseline.service_fee,
            discount_amount=arm.discount_amount + self.baseline.discount_amount,
            free_delivery_threshold=self.baseline.free_delivery_threshold,
        )
        return base.total_customer_price(basket)
