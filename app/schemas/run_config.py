from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class RunConfig(BaseModel):
    seed: int = Field(..., description="RNG seed for reproducibility")
    horizon_days: int = Field(90, ge=1, le=500)
    baseline_end_day: int = Field(30, ge=1)
    experiment_start_day: int = Field(31, ge=2)
    customer_count: int = Field(100, ge=1, le=50_000)

    baseline_order_price: float = Field(15.0, ge=0)
    baseline_delivery_fee: float = Field(2.99, ge=0)
    baseline_service_fee: float = Field(1.0, ge=0)
    baseline_discount: float = Field(0.0, ge=0)
    free_delivery_threshold: float | None = Field(25.0, ge=0)

    control_delivery_fee: float = Field(2.99, ge=0)
    variant_delivery_fee: float = Field(1.99, ge=0)
    variant_extra_discount: float = Field(
        0.0, ge=0, description="Optional promo discount on variant arm only"
    )

    variable_cost_rate: float = Field(0.35, ge=0, le=1)

    budget_mean: float = Field(40.0, ge=1)
    budget_std: float = Field(12.0, ge=0.1)
    propensity_alpha: float = Field(2.0, ge=0.1)
    propensity_beta: float = Field(5.0, ge=0.1)
    basket_log_mean: float = Field(2.2, ge=0)
    basket_log_sigma: float = Field(0.35, ge=0.01)

    zones: list[str] = Field(default_factory=lambda: ["A", "B", "C"])
    zone_weights: list[float] = Field(default_factory=lambda: [0.5, 0.3, 0.2])

    weekend_factor: float = Field(1.12, ge=0.1)
    weekday_factor: float = Field(1.0, ge=0.1)
    seasonal_amplitude: float = Field(0.05, ge=0)
    zone_modifiers: dict[str, float] | None = None

    promo_first_order_only: bool = False
    promo_max_uses_per_customer: int = Field(999, ge=1)
    promo_cooldown_days: int = Field(0, ge=0)
    campaign_budget: float | None = Field(None, ge=0)

    @model_validator(mode="after")
    def check_phases(self) -> RunConfig:
        if self.experiment_start_day <= 1:
            raise ValueError("experiment_start_day must be > 1")
        if self.baseline_end_day >= self.experiment_start_day:
            raise ValueError("baseline_end_day must be < experiment_start_day")
        if len(self.zones) != len(self.zone_weights):
            raise ValueError("zones and zone_weights length must match")
        return self

    def to_json(self) -> dict[str, Any]:
        return self.model_dump()
