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

    customers_evaluated: int = Field(
        ...,
        description="Active (non-churned) customers evaluated on this day in this aggregate slice",
    )
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
    active_customers_evaluated: int = Field(
        ...,
        description="Same value as customers_evaluated (spec-friendly alias for “active” count)",
    )


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
    segment: str
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
    purchase_count_after_event: int
    days_since_last_purchase: int | None


class ExperimentArmStatsOut(BaseModel):
    """Aggregated experiment-phase counts for one treatment arm."""

    model_config = ConfigDict(extra="forbid")

    treatment: str
    customer_days: int
    orders: int
    conversion_rate: float
    conversion_rate_wilson_low: float
    conversion_rate_wilson_high: float
    net_revenue: float
    contribution_margin: float


class BayesianArmStatsOut(BaseModel):
    """Beta–binomial posterior summary for one arm (conversion on customer-days)."""

    model_config = ConfigDict(extra="forbid")

    treatment: str
    posterior_alpha: float = Field(
        ...,
        description="Beta posterior alpha after orders and customer-days",
    )
    posterior_beta: float
    conversion_rate_posterior_mean: float = Field(
        ...,
        description="Posterior mean conversion rate α/(α+β)",
    )
    conversion_rate_credible_low: float = Field(
        ...,
        description="Equal-tailed credible bound (2.5% quantile of posterior draws)",
    )
    conversion_rate_credible_high: float = Field(
        ...,
        description="Equal-tailed credible bound (97.5% quantile of posterior draws)",
    )


class BayesianComparisonOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prob_variant_superior: float = Field(
        ...,
        description="P(variant conversion > control | data); independent Beta posteriors",
    )
    lift_absolute_mean: float
    lift_absolute_median: float
    lift_relative_mean: float | None = Field(
        None,
        description="Mean of (p_v−p_c)/p_c over draws with p_c > epsilon; null if no such draws",
    )
    lift_relative_median: float | None = Field(
        None,
        description="Median of (p_v−p_c)/p_c over draws with p_c > epsilon; null if no such draws",
    )
    relative_lift_effective_sample_fraction: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of MC draws where p_c exceeded relative_lift_p_c_epsilon",
    )


class BayesianExperimentInferenceOut(BaseModel):
    """Bayesian Beta-binomial analysis for experiment-phase conversion."""

    model_config = ConfigDict(extra="forbid")

    prior_alpha: float
    prior_beta: float
    mc_samples: int
    relative_lift_p_c_epsilon: float
    control: BayesianArmStatsOut
    variant: BayesianArmStatsOut
    comparison: BayesianComparisonOut


class ExperimentInferenceOut(BaseModel):
    """Run-level experiment summary with spec §9 style inference."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    control: ExperimentArmStatsOut
    variant: ExperimentArmStatsOut
    conversion_lift_absolute: float
    conversion_lift_relative: float
    two_proportion_z_statistic: float
    two_proportion_p_value_two_sided: float
    bayesian: BayesianExperimentInferenceOut


class BatchCreateRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ids: list[str]
    status: str


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
