"""Pydantic model for POST /api/runs body and shared engine configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class RunConfig(BaseModel):
    """Validated payload for creating a simulation run (API body and engine input)."""

    seed: int = Field(..., description="RNG seed for reproducibility")
    horizon_days: int = Field(90, ge=1, le=500)
    baseline_end_day: int = Field(30, ge=1)
    experiment_start_day: int = Field(31, ge=2)
    customer_count: int = Field(100, ge=1, le=50_000)

    baseline_order_price: float = Field(
        15.0,
        ge=0,
        deprecated=True,
        description=(
            "Deprecated — not used in the live pricing path. Baskets are sampled from a "
            "lognormal distribution parameterised by basket_log_mean/basket_log_sigma. "
            "Predictive CLV uses each customer's basket_mean instead of this field."
        ),
    )
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

    channel_propensity_modifiers: dict[str, float] | None = Field(
        None,
        description=(
            "Per-channel multiplier applied to buy_propensity at cohort generation time. "
            "Keys must match the channels drawn during cohort creation "
            "(organic, paid, referral). Defaults to {organic: 1.0, paid: 0.85, referral: 1.15} "
            "when None."
        ),
    )

    zones: list[str] = Field(default_factory=lambda: ["A", "B", "C"])
    zone_weights: list[float] = Field(default_factory=lambda: [0.5, 0.3, 0.2])

    weekend_factor: float = Field(1.12, ge=0.1)
    weekday_factor: float = Field(1.0, ge=0.1)
    seasonal_amplitude: float = Field(0.05, ge=0)
    zone_modifiers: dict[str, float] | None = None

    treatment_split: float = Field(
        0.5,
        ge=0.01,
        le=0.99,
        description="Fraction of customers assigned to the variant arm (default 0.5 = 50/50)",
    )

    promo_first_order_only: bool = False
    promo_max_uses_per_customer: int = Field(999, ge=1)
    promo_cooldown_days: int = Field(0, ge=0)
    campaign_budget: float | None = Field(None, ge=0)

    churn_base_rate: float = Field(
        0.002, ge=0, le=1, description="Daily churn hazard for a customer at floor retention score"
    )
    clv_projected_days: int = Field(
        90, ge=1, description="Forward horizon (days) used in predictive CLV formula"
    )
    discount_rate_annual: float = Field(
        0.10, ge=0, description="Annual discount rate applied in DCF CLV calculation"
    )
    clv_validation_days: int = Field(
        0,
        ge=0,
        description=(
            "Extra days simulated at baseline pricing after the horizon "
            "to validate CLV predictions (0 = disabled)"
        ),
    )

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
