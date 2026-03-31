"""Frequentist and Beta-binomial Bayesian experiment inference (spec section 9)."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_aggregate import DailyAggregateRow
from app.schemas.api_responses import (
    BayesianArmStatsOut,
    BayesianComparisonOut,
    BayesianExperimentInferenceOut,
    ExperimentArmStatsOut,
    ExperimentInferenceOut,
)

# Fixed MC setup for reproducible API responses (numpy Gamma–Beta, no scipy).
BAYESIAN_MC_SAMPLES = 100_000
BAYESIAN_MC_SEED = 42
RELATIVE_LIFT_P_C_EPSILON = 1e-6


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score binomial confidence interval for proportion successes/n."""
    if n <= 0:
        return (0.0, 0.0)
    phat = successes / n
    denom = 1.0 + z**2 / n
    centre = phat + z**2 / (2 * n)
    margin = z * math.sqrt((phat * (1.0 - phat) + z**2 / (4 * n)) / n)
    low = max(0.0, (centre - margin) / denom)
    high = min(1.0, (centre + margin) / denom)
    return (low, high)


def two_proportion_z_test_p_value(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """Pooled two-proportion z-test; returns (z_statistic, two-sided p-value)."""
    if n1 <= 0 or n2 <= 0:
        return (0.0, 1.0)
    p1 = x1 / n1
    p2 = x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    if p_pool <= 0 or p_pool >= 1:
        return (0.0, 1.0)
    se = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n1 + 1.0 / n2))
    if se <= 0:
        return (0.0, 1.0)
    z_stat = (p1 - p2) / se
    p_two = 2.0 * _normal_cdf(-abs(z_stat))
    return (z_stat, min(1.0, max(0.0, p_two)))


def beta_posterior_hparams(
    successes: int, n: int, prior_alpha: float, prior_beta: float
) -> tuple[float, float]:
    """Conjugate Beta posterior parameters after Binomial(n, p) with x successes."""
    failures = max(0, n - successes)
    return prior_alpha + float(successes), prior_beta + float(failures)


def _sample_beta_ratios(
    alpha: float, beta: float, size: int, rng: np.random.Generator
) -> np.ndarray:
    """Draw samples from Beta(alpha, beta) via independent Gamma ratios."""
    g1 = rng.gamma(alpha, 1.0, size=size)
    g2 = rng.gamma(beta, 1.0, size=size)
    return g1 / (g1 + g2)


@dataclass
class ExperimentArmRollup:
    """Sums of daily aggregate metrics for one treatment arm over the experiment phase."""

    customer_days: int = 0
    orders: int = 0
    net_revenue: float = 0.0
    contribution_margin: float = 0.0


def load_experiment_arm_rollups(
    db: Session, run_id: uuid.UUID
) -> tuple[ExperimentArmRollup, ExperimentArmRollup]:
    """Sum experiment-phase daily aggregates per arm (zone slice ``__all__``)."""
    rows = db.scalars(
        select(DailyAggregateRow).where(
            DailyAggregateRow.run_id == run_id,
            DailyAggregateRow.phase == "experiment",
            DailyAggregateRow.location_zone == "__all__",
        )
    ).all()
    ctrl = ExperimentArmRollup()
    var = ExperimentArmRollup()
    for row in rows:
        m = row.metrics
        if row.treatment == "control":
            ctrl.customer_days += m["customers_evaluated"]
            ctrl.orders += m["orders"]
            ctrl.net_revenue += m["net_revenue"]
            ctrl.contribution_margin += m["contribution_margin"]
        elif row.treatment == "variant":
            var.customer_days += m["customers_evaluated"]
            var.orders += m["orders"]
            var.net_revenue += m["net_revenue"]
            var.contribution_margin += m["contribution_margin"]
    return ctrl, var


def build_bayesian_experiment_inference(
    *,
    control: ExperimentArmRollup,
    variant: ExperimentArmRollup,
    prior_alpha: float,
    prior_beta: float,
    mc_samples: int = BAYESIAN_MC_SAMPLES,
    rng_seed: int = BAYESIAN_MC_SEED,
    relative_lift_epsilon: float = RELATIVE_LIFT_P_C_EPSILON,
) -> BayesianExperimentInferenceOut:
    """Beta–binomial posteriors per arm; independent posteriors for P(variant > control)."""
    ca, cb = beta_posterior_hparams(control.orders, control.customer_days, prior_alpha, prior_beta)
    va, vb = beta_posterior_hparams(variant.orders, variant.customer_days, prior_alpha, prior_beta)

    mean_c = ca / (ca + cb) if (ca + cb) > 0 else 0.0
    mean_v = va / (va + vb) if (va + vb) > 0 else 0.0

    rng = np.random.default_rng(rng_seed)
    n = max(1, mc_samples)
    p_c = _sample_beta_ratios(ca, cb, n, rng)
    p_v = _sample_beta_ratios(va, vb, n, rng)

    q_lo, q_hi = 0.025, 0.975
    cred_c = (float(np.quantile(p_c, q_lo)), float(np.quantile(p_c, q_hi)))
    cred_v = (float(np.quantile(p_v, q_lo)), float(np.quantile(p_v, q_hi)))

    prob_sup = float(np.mean(p_v > p_c))
    abs_lift = p_v - p_c
    lift_abs_mean = float(np.mean(abs_lift))
    lift_abs_med = float(np.median(abs_lift))

    mask = p_c > relative_lift_epsilon
    n_eff = int(np.sum(mask))
    frac = n_eff / float(n)
    if n_eff > 0:
        rel = abs_lift[mask] / p_c[mask]
        rel_mean = float(np.mean(rel))
        rel_med = float(np.median(rel))
    else:
        rel_mean = None
        rel_med = None

    return BayesianExperimentInferenceOut(
        prior_alpha=prior_alpha,
        prior_beta=prior_beta,
        mc_samples=mc_samples,
        relative_lift_p_c_epsilon=relative_lift_epsilon,
        control=BayesianArmStatsOut(
            treatment="control",
            posterior_alpha=ca,
            posterior_beta=cb,
            conversion_rate_posterior_mean=mean_c,
            conversion_rate_credible_low=cred_c[0],
            conversion_rate_credible_high=cred_c[1],
        ),
        variant=BayesianArmStatsOut(
            treatment="variant",
            posterior_alpha=va,
            posterior_beta=vb,
            conversion_rate_posterior_mean=mean_v,
            conversion_rate_credible_low=cred_v[0],
            conversion_rate_credible_high=cred_v[1],
        ),
        comparison=BayesianComparisonOut(
            prob_variant_superior=prob_sup,
            lift_absolute_mean=lift_abs_mean,
            lift_absolute_median=lift_abs_med,
            lift_relative_mean=rel_mean,
            lift_relative_median=rel_med,
            relative_lift_effective_sample_fraction=frac,
        ),
    )


def build_experiment_inference(
    *,
    run_id: str,
    control: ExperimentArmRollup,
    variant: ExperimentArmRollup,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
) -> ExperimentInferenceOut:
    p_c = control.orders / control.customer_days if control.customer_days else 0.0
    p_v = variant.orders / variant.customer_days if variant.customer_days else 0.0
    w_c = wilson_interval(control.orders, control.customer_days)
    w_v = wilson_interval(variant.orders, variant.customer_days)
    z_stat, p_val = two_proportion_z_test_p_value(
        control.orders, control.customer_days, variant.orders, variant.customer_days
    )
    lift_abs = p_v - p_c
    lift_rel = lift_abs / p_c if p_c > 0 else 0.0

    bayesian = build_bayesian_experiment_inference(
        control=control,
        variant=variant,
        prior_alpha=prior_alpha,
        prior_beta=prior_beta,
    )

    return ExperimentInferenceOut(
        run_id=run_id,
        control=ExperimentArmStatsOut(
            treatment="control",
            customer_days=control.customer_days,
            orders=control.orders,
            conversion_rate=p_c,
            conversion_rate_wilson_low=w_c[0],
            conversion_rate_wilson_high=w_c[1],
            net_revenue=control.net_revenue,
            contribution_margin=control.contribution_margin,
        ),
        variant=ExperimentArmStatsOut(
            treatment="variant",
            customer_days=variant.customer_days,
            orders=variant.orders,
            conversion_rate=p_v,
            conversion_rate_wilson_low=w_v[0],
            conversion_rate_wilson_high=w_v[1],
            net_revenue=variant.net_revenue,
            contribution_margin=variant.contribution_margin,
        ),
        conversion_lift_absolute=lift_abs,
        conversion_lift_relative=lift_rel,
        two_proportion_z_statistic=z_stat,
        two_proportion_p_value_two_sided=p_val,
        bayesian=bayesian,
    )
