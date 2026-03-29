from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaselinePolicy:
    order_price: float
    delivery_fee: float
    service_fee: float
    discount_amount: float = 0.0
    free_delivery_threshold: float | None = None

    def total_customer_price(self, subtotal: float) -> float:
        delivery = self.delivery_fee
        if (
            self.free_delivery_threshold is not None
            and subtotal >= self.free_delivery_threshold
        ):
            delivery = 0.0
        return subtotal + delivery + self.service_fee - self.discount_amount


@dataclass(frozen=True)
class ExperimentArm:
    name: str
    delivery_fee: float
    discount_amount: float = 0.0


@dataclass(frozen=True)
class PricingPolicy:
    baseline: BaselinePolicy
    control: ExperimentArm
    variant: ExperimentArm

    def arm_for_treatment(self, treatment: str | None) -> ExperimentArm:
        if treatment == "variant":
            return self.variant
        return self.control

    def baseline_total(self, basket: float) -> float:
        return self.baseline.total_customer_price(basket)

    def experiment_total(self, basket: float, treatment: str | None) -> float:
        arm = self.arm_for_treatment(treatment)
        base = BaselinePolicy(
            order_price=0.0,
            delivery_fee=arm.delivery_fee,
            service_fee=self.baseline.service_fee,
            discount_amount=arm.discount_amount + self.baseline.discount_amount,
            free_delivery_threshold=self.baseline.free_delivery_threshold,
        )
        return base.total_customer_price(basket)
