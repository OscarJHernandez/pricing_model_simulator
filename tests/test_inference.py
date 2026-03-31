"""Wilson interval, two-proportion z-test, and Beta–binomial Bayesian block (spec section 9)."""

import pytest

from app.services.stats.inference import (
    BAYESIAN_MC_SEED,
    ExperimentArmRollup,
    beta_posterior_hparams,
    build_bayesian_experiment_inference,
    build_experiment_inference,
    two_proportion_z_test_p_value,
    wilson_interval,
)


def test_wilson_interval_bounds():
    low, high = wilson_interval(50, 100)
    assert 0.0 <= low < high <= 1.0
    assert low < 0.5 < high


def test_wilson_empty_n():
    low, high = wilson_interval(0, 0)
    assert low == 0.0 and high == 0.0


def test_two_proportion_symmetric():
    z, p = two_proportion_z_test_p_value(50, 100, 50, 100)
    assert abs(z) < 1e-9
    assert p > 0.99


def test_build_experiment_inference_lift():
    ctrl = ExperimentArmRollup(
        customer_days=1000, orders=100, net_revenue=1000.0, contribution_margin=400.0
    )
    var = ExperimentArmRollup(
        customer_days=1000, orders=120, net_revenue=1200.0, contribution_margin=500.0
    )
    out = build_experiment_inference(run_id="x", control=ctrl, variant=var)
    assert out.conversion_lift_absolute == pytest.approx(0.02)
    assert out.control.conversion_rate == 0.1
    assert out.variant.conversion_rate == 0.12
    assert 0 <= out.two_proportion_p_value_two_sided <= 1
    assert out.bayesian.prior_alpha == 1.0
    assert out.bayesian.prior_beta == 1.0
    assert out.bayesian.control.posterior_alpha == pytest.approx(101.0)
    assert out.bayesian.control.posterior_beta == pytest.approx(901.0)
    assert out.bayesian.variant.posterior_alpha == pytest.approx(121.0)
    assert out.bayesian.variant.posterior_beta == pytest.approx(881.0)
    assert 0.0 <= out.bayesian.comparison.prob_variant_superior <= 1.0
    assert out.bayesian.comparison.prob_variant_superior > 0.9
    assert out.bayesian.comparison.lift_absolute_mean == pytest.approx(0.02, abs=0.01)


def test_beta_posterior_jeffreys():
    ctrl = ExperimentArmRollup(customer_days=100, orders=10)
    var = ExperimentArmRollup(customer_days=100, orders=10)
    out = build_experiment_inference(
        run_id="y", control=ctrl, variant=var, prior_alpha=0.5, prior_beta=0.5
    )
    assert out.bayesian.control.posterior_alpha == pytest.approx(10.5)
    assert out.bayesian.control.posterior_beta == pytest.approx(90.5)
    assert out.bayesian.comparison.prob_variant_superior == pytest.approx(0.5, abs=0.02)


def test_beta_posterior_hparams():
    a, b = beta_posterior_hparams(3, 10, 1.0, 1.0)
    assert a == 4.0 and b == 8.0


def test_bayesian_reproducible_seed():
    ctrl = ExperimentArmRollup(customer_days=500, orders=50)
    var = ExperimentArmRollup(customer_days=500, orders=80)
    b1 = build_bayesian_experiment_inference(
        control=ctrl, variant=var, prior_alpha=1.0, prior_beta=1.0, rng_seed=BAYESIAN_MC_SEED
    )
    b2 = build_bayesian_experiment_inference(
        control=ctrl, variant=var, prior_alpha=1.0, prior_beta=1.0, rng_seed=BAYESIAN_MC_SEED
    )
    assert b1.comparison.prob_variant_superior == b2.comparison.prob_variant_superior
    assert b1.comparison.lift_absolute_mean == b2.comparison.lift_absolute_mean


def test_frequentist_unchanged_when_prior_changes():
    ctrl = ExperimentArmRollup(customer_days=200, orders=40)
    var = ExperimentArmRollup(customer_days=200, orders=50)
    o1 = build_experiment_inference(
        run_id="a", control=ctrl, variant=var, prior_alpha=1.0, prior_beta=1.0
    )
    o2 = build_experiment_inference(
        run_id="a", control=ctrl, variant=var, prior_alpha=5.0, prior_beta=5.0
    )
    assert o1.two_proportion_z_statistic == o2.two_proportion_z_statistic
    assert o1.two_proportion_p_value_two_sided == o2.two_proportion_p_value_two_sided
    assert o1.control.conversion_rate_wilson_low == o2.control.conversion_rate_wilson_low
    assert o1.bayesian.control.posterior_alpha != o2.bayesian.control.posterior_alpha
