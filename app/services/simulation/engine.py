"""Day-by-day simulation: cohort generation, pricing, stochastic orders, and DB persistence."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Literal, TypedDict

import numpy as np
from sqlalchemy.orm import Session

from app.domain.customer import Customer, PurchaseContext, derive_segment
from app.models.customer import CustomerRow
from app.models.customer_lifetime import CustomerLifetimeRow
from app.models.daily_aggregate import DailyAggregateRow
from app.models.daily_customer_outcome import DailyCustomerOutcomeRow
from app.models.experiment_assignment import ExperimentAssignmentRow
from app.models.promo_budget import PromoBudgetTrackingRow
from app.models.run_parameter import RunParameterRow
from app.models.simulation_run import SimulationRunRow
from app.schemas.run_config import RunConfig
from app.services.metrics.aggregation import build_day_metrics
from app.services.pricing.geographic import zone_multiplier
from app.services.pricing.policies import BaselinePolicy, ExperimentArm, PricingPolicy
from app.services.pricing.promo import PromoRules, promo_eligible
from app.services.pricing.temporal import is_weekend, temporal_multiplier
from app.services.simulation.assignment import assign_treatments

SimulationPhase = Literal["baseline", "washout", "experiment"]


class _DayAggBucket(TypedDict):
    """Mutable counters for one (phase, treatment, zone) slice before `build_day_metrics`."""

    n: int
    orders: int
    gross: float
    disc: float
    net: float
    vc: float
    cm: float
    buyers: int
    repeat_buyers: int
    ever_before: int
    inc_orders: int
    inc_rev: float
    inc_margin: float
    non_inc_disc: float


_DEFAULT_CHANNEL_MODIFIERS: dict[str, float] = {
    "organic": 1.0,
    "paid": 0.85,
    "referral": 1.15,
}


def generate_customers(config: RunConfig, rng: np.random.Generator) -> list[Customer]:
    """Draw a cohort of synthetic customers from ``RunConfig`` distribution parameters."""
    customers: list[Customer] = []
    z = np.array(config.zone_weights, dtype=float)
    z = z / z.sum()
    channel_mods = config.channel_propensity_modifiers or _DEFAULT_CHANNEL_MODIFIERS
    for i in range(config.customer_count):
        budget = max(8.0, float(rng.normal(config.budget_mean, config.budget_std)))
        buy_propensity = float(rng.beta(config.propensity_alpha, config.propensity_beta))
        buy_propensity = min(0.95, max(0.02, buy_propensity))
        price_threshold = float(rng.uniform(0.35, 0.85) * budget)
        repeat_boost = float(rng.uniform(0.15, 0.55))
        basket_mean = float(rng.lognormal(config.basket_log_mean, config.basket_log_sigma))
        basket_mean = max(4.0, basket_mean)
        zone = str(rng.choice(config.zones, p=z))
        rs = float(rng.uniform(0.2, 0.9))
        ps = float(rng.uniform(0.2, 0.9))
        ch = str(rng.choice(list(channel_mods.keys())))
        ch_modifier = channel_mods.get(ch, 1.0)
        seg = derive_segment(budget, price_threshold, buy_propensity)
        customers.append(
            Customer(
                customer_id=-1,
                customer_index=i,
                budget=budget,
                buy_propensity=buy_propensity,
                price_threshold=price_threshold,
                repeat_boost=repeat_boost,
                basket_mean=basket_mean,
                location_zone=zone,
                segment=seg,
                acquisition_channel=ch,
                channel_propensity_modifier=ch_modifier,
                retention_sensitivity=rs,
                promo_sensitivity=ps,
            )
        )
    return customers


def _pricing_for_config(config: RunConfig) -> PricingPolicy:
    """Map numeric config fields to immutable policy objects used each day."""
    baseline = BaselinePolicy(
        delivery_fee=config.baseline_delivery_fee,
        service_fee=config.baseline_service_fee,
        discount_amount=config.baseline_discount,
        free_delivery_threshold=config.free_delivery_threshold,
    )
    control = ExperimentArm("control", delivery_fee=config.control_delivery_fee)
    variant = ExperimentArm(
        "variant",
        delivery_fee=config.variant_delivery_fee,
        discount_amount=config.variant_extra_discount,
    )
    return PricingPolicy(baseline=baseline, control=control, variant=variant)


def _sample_basket(customer: Customer, rng: np.random.Generator) -> float:
    """Lognormal basket subtotal around the customer's ``basket_mean`` with fixed noise."""
    v = float(rng.lognormal(math.log(max(customer.basket_mean, 1.0)), 0.25))
    return max(3.0, v)


def _price_breakdown(
    policy: PricingPolicy,
    *,
    phase: SimulationPhase,
    basket: float,
    treatment: str | None,
    promo_ok: bool,
) -> tuple[float, float, float, float]:
    """Compute list price components for the active phase and treatment.

    Returns:
        offered_total: Price the customer faces (variant may include promo discount).
        gross_list: Pre-discount sum of basket + list delivery + service.
        discount_amount: Total discount applied on this offer (baseline + variant extra).
        counterfactual_control: Control-arm total used to define incrementality when
            the customer is on variant (same basket, promo rules).
    """
    service = policy.baseline.service_fee
    base_disc = policy.baseline.discount_amount
    fd = policy.baseline.free_delivery_threshold

    def delivery_charge(fee: float) -> float:
        if fd is not None and basket >= fd:
            return 0.0
        return fee

    if phase == "baseline":
        d = delivery_charge(policy.baseline.delivery_fee)
        total = basket + d + service - base_disc
        gross_list = basket + policy.baseline.delivery_fee + service
        return total, gross_list, base_disc, total

    ctrl_deliv = delivery_charge(policy.control.delivery_fee)
    ctrl_total = basket + ctrl_deliv + service - base_disc

    if treatment == "control":
        return ctrl_total, basket + policy.control.delivery_fee + service, base_disc, ctrl_total

    var_deliv = delivery_charge(policy.variant.delivery_fee)
    extra = policy.variant.discount_amount if promo_ok else 0.0
    disc = base_disc + extra
    var_total = basket + var_deliv + service - disc
    gross_list = basket + policy.variant.delivery_fee + service
    return var_total, gross_list, disc, ctrl_total


def execute_simulation(db: Session, run_id: uuid.UUID, config: RunConfig) -> None:
    """Run all horizon days, persisting customers, outcomes, aggregates, and promo tracking.

    Expects the run row to exist; callers typically set status to ``running`` first.
    Commits once at the end with status ``completed``, or relies on the job wrapper
    to mark ``failed`` on exceptions.
    """
    rng = np.random.default_rng(config.seed)
    policy = _pricing_for_config(config)
    promo_rules = PromoRules(
        first_order_only=config.promo_first_order_only,
        max_uses_per_customer=config.promo_max_uses_per_customer,
        cooldown_days=config.promo_cooldown_days,
        campaign_budget=config.campaign_budget,
    )

    customers = generate_customers(config, rng)
    assign_treatments(customers, rng, split=config.treatment_split)

    rows: list[CustomerRow] = []
    for c in customers:
        rows.append(
            CustomerRow(
                run_id=run_id,
                customer_index=c.customer_index,
                budget=c.budget,
                buy_propensity=c.buy_propensity,
                price_threshold=c.price_threshold,
                repeat_boost=c.repeat_boost,
                basket_mean=c.basket_mean,
                segment=c.segment,
                location_zone=c.location_zone,
                acquisition_channel=c.acquisition_channel,
                retention_sensitivity=c.retention_sensitivity,
                promo_sensitivity=c.promo_sensitivity,
            )
        )
    db.add_all(rows)
    db.flush()
    for c, r in zip(customers, rows, strict=True):
        c.customer_id = r.id

    for c in customers:
        db.add(
            ExperimentAssignmentRow(
                run_id=run_id,
                customer_id=c.customer_id,
                treatment=c.assigned_treatment or "control",
            )
        )
    db.flush()

    cumulative_discount = 0.0

    for day in range(1, config.horizon_days + 1):
        t_mult = temporal_multiplier(
            day,
            weekend_factor=config.weekend_factor,
            weekday_factor=config.weekday_factor,
            seasonal_amplitude=config.seasonal_amplitude,
        )
        wknd = is_weekend(day)

        if day <= config.baseline_end_day:
            phase: SimulationPhase = "baseline"
        elif day < config.experiment_start_day:
            phase = "washout"
        else:
            phase = "experiment"

        day_outcomes: list[DailyCustomerOutcomeRow] = []
        agg_buckets: dict[tuple[SimulationPhase, str | None, str], _DayAggBucket] = {}

        for c in customers:
            if not c.is_active:
                continue

            if c.last_purchase_day is not None:
                c.decay_retention(day - c.last_purchase_day)

            if rng.random() < c.compute_churn_probability(config.churn_base_rate):
                c.is_active = False
                c.churned_day = day
                continue

            basket = _sample_basket(c, rng)
            treat = c.assigned_treatment if phase == "experiment" else None
            prior_purchases = c.purchase_count
            days_since_lp = None if c.last_purchase_day is None else int(day - c.last_purchase_day)

            promo_ok = promo_eligible(c, day, promo_rules, cumulative_discount)
            geo_m = zone_multiplier(c.location_zone, config.zone_modifiers)
            # Only variant arm customers during the experiment phase can be ineligible for a
            # promo discount; baseline/control customers were never offered one, so the 0.85
            # demand haircut in compute_purchase_probability must not apply to them.
            ctx_promo = promo_ok if (phase == "experiment" and treat == "variant") else True
            ctx = PurchaseContext(
                temporal_multiplier=t_mult,
                geographic_multiplier=geo_m,
                promo_eligible=ctx_promo,
                is_weekend=wknd,
            )

            offered, _gross_list, disc_amt, cf_price = _price_breakdown(
                policy,
                phase=phase,
                basket=basket,
                treatment=treat,
                promo_ok=promo_ok,
            )

            p_treat = c.compute_purchase_probability(offered, day, ctx)
            if phase == "experiment" and treat == "variant":
                p_ctrl = c.compute_purchase_probability(cf_price, day, ctx)
            elif phase == "experiment":
                p_ctrl = p_treat
            else:
                p_ctrl = p_treat

            u = float(rng.random())
            purchased = u < p_treat
            cf_buy = u < p_ctrl
            incremental = bool(
                purchased and phase == "experiment" and treat == "variant" and not cf_buy
            )

            order_value = 0.0
            gross_rev = 0.0
            net_rev = 0.0
            var_cost = 0.0
            margin = 0.0
            if purchased:
                order_value = offered
                gross_rev = (
                    basket
                    + (
                        policy.baseline.delivery_fee
                        if phase == "baseline"
                        else (
                            policy.variant.delivery_fee
                            if treat == "variant"
                            else policy.control.delivery_fee
                        )
                    )
                    + policy.baseline.service_fee
                )
                net_rev = offered
                var_cost = config.variable_cost_rate * basket
                margin = net_rev - var_cost
                cumulative_discount += disc_amt
                if treat == "variant" and promo_ok and policy.variant.discount_amount > 0:
                    c.promo_uses_to_date += 1
                    c.last_promo_day = day
                c.register_purchase(day, order_value, variable_cost=var_cost)

            row = DailyCustomerOutcomeRow(
                run_id=run_id,
                day=day,
                customer_id=c.customer_id,
                phase=phase,
                treatment=treat,
                offered_total_price=offered,
                purchase_probability=p_treat,
                purchased=purchased,
                order_value=order_value,
                gross_revenue=gross_rev if purchased else 0.0,
                discount_amount=disc_amt if purchased else 0.0,
                net_revenue=net_rev if purchased else 0.0,
                variable_cost=var_cost if purchased else 0.0,
                contribution_margin=margin if purchased else 0.0,
                incremental_order=incremental,
                counterfactual_would_buy=cf_buy,
                purchase_count_after_event=c.purchase_count,
                days_since_last_purchase=days_since_lp,
            )
            day_outcomes.append(row)

            had_prior = prior_purchases > 0
            for zn in ("__all__", c.location_zone):
                k = (phase, treat, zn)
                if k not in agg_buckets:
                    agg_buckets[k] = {
                        "n": 0,
                        "orders": 0,
                        "gross": 0.0,
                        "disc": 0.0,
                        "net": 0.0,
                        "vc": 0.0,
                        "cm": 0.0,
                        "buyers": 0,
                        "repeat_buyers": 0,
                        "ever_before": 0,
                        "inc_orders": 0,
                        "inc_rev": 0.0,
                        "inc_margin": 0.0,
                        "non_inc_disc": 0.0,
                    }
                b = agg_buckets[k]
                b["n"] += 1
                if had_prior:
                    b["ever_before"] += 1
                if purchased:
                    b["orders"] += 1
                    b["gross"] += gross_rev
                    b["disc"] += disc_amt
                    b["net"] += net_rev
                    b["vc"] += var_cost
                    b["cm"] += margin
                    b["buyers"] += 1
                    if had_prior:
                        b["repeat_buyers"] += 1
                    if incremental:
                        b["inc_orders"] += 1
                        b["inc_rev"] += net_rev
                        b["inc_margin"] += margin
                    if disc_amt > 0 and cf_buy:
                        b["non_inc_disc"] += disc_amt

        db.add_all(day_outcomes)

        for (ph, tr, zn), b in agg_buckets.items():
            metrics = build_day_metrics(
                customers_evaluated=b["n"],
                orders=b["orders"],
                gross_revenue=b["gross"],
                discount_spend=b["disc"],
                net_revenue=b["net"],
                variable_cost=b["vc"],
                contribution_margin=b["cm"],
                buyers_today=b["buyers"],
                repeat_buyers_today=b["repeat_buyers"],
                customers_ever_purchased_before=b["ever_before"],
                incremental_orders=b["inc_orders"],
                incremental_revenue=b["inc_rev"],
                incremental_margin=b["inc_margin"],
                non_incremental_discount_spend=b["non_inc_disc"],
            )
            db.add(
                DailyAggregateRow(
                    run_id=run_id,
                    day=day,
                    phase=ph,
                    treatment=tr,
                    location_zone=zn,
                    metrics=metrics,
                )
            )

        day_discount = sum(o.discount_amount for o in day_outcomes if o.purchased)
        db.add(
            PromoBudgetTrackingRow(
                run_id=run_id,
                day=day,
                discount_spend_day=day_discount,
                cumulative_discount_spend=cumulative_discount,
                remaining_budget=(
                    (config.campaign_budget - cumulative_discount)
                    if config.campaign_budget is not None
                    else None
                ),
            )
        )
        db.flush()

    # --- CLV snapshot at end of main horizon ---
    # Use a neutral baseline context (no calendar or geo effects) to compute predicted CLV
    # at the last-active state of each customer. Each customer's own basket_mean is used as
    # the basket subtotal so the price reflects their individual spending level, not a
    # global config constant (baseline_order_price is legacy and not used in the pricing path).
    clv_context = PurchaseContext(
        temporal_multiplier=1.0,
        geographic_multiplier=1.0,
        promo_eligible=True,
        is_weekend=False,
    )
    for c in customers:
        clv_basket_price = (
            c.basket_mean
            + config.baseline_delivery_fee
            + config.baseline_service_fee
            - config.baseline_discount
        )
        c.predicted_clv = c.compute_predictive_clv(
            projected_days=config.clv_projected_days,
            discount_rate_annual=config.discount_rate_annual,
            churn_base_rate=config.churn_base_rate,
            offered_price=clv_basket_price,
            current_day=config.horizon_days,
            context=clv_context,
        )

    # Snapshot horizon-only stats before the optional validation extension runs.
    # Validation purchases must not pollute the realized horizon counters.
    horizon_orders = {c.customer_id: c.purchase_count for c in customers}
    horizon_net_revenue = {c.customer_id: c.cumulative_net_revenue for c in customers}
    horizon_cm = {c.customer_id: c.cumulative_contribution_margin for c in customers}
    horizon_days_active = {
        c.customer_id: (c.churned_day - 1 if c.churned_day is not None else config.horizon_days)
        for c in customers
    }

    # --- Optional validation extension (baseline pricing only, no experiment arms) ---
    # These extra days are run solely to collect actual realized revenue for CLV comparison.
    # They are NOT written to daily_aggregate or daily_customer_outcomes.
    clv_validation_revenue: dict[int, float] = {c.customer_id: 0.0 for c in customers}
    if config.clv_validation_days > 0:
        for val_day in range(
            config.horizon_days + 1, config.horizon_days + config.clv_validation_days + 1
        ):
            t_mult = temporal_multiplier(
                val_day,
                weekend_factor=config.weekend_factor,
                weekday_factor=config.weekday_factor,
                seasonal_amplitude=config.seasonal_amplitude,
            )
            wknd = is_weekend(val_day)
            for c in customers:
                if not c.is_active:
                    continue
                if c.last_purchase_day is not None:
                    c.decay_retention(val_day - c.last_purchase_day)
                basket = _sample_basket(c, rng)
                geo_m = zone_multiplier(c.location_zone, config.zone_modifiers)
                ctx = PurchaseContext(
                    temporal_multiplier=t_mult,
                    geographic_multiplier=geo_m,
                    promo_eligible=True,
                    is_weekend=wknd,
                )
                offered = (
                    basket
                    + config.baseline_delivery_fee
                    + config.baseline_service_fee
                    - config.baseline_discount
                )
                p = c.compute_purchase_probability(offered, val_day, ctx)
                if rng.random() < p:
                    clv_validation_revenue[c.customer_id] += offered
                    # Update retention state so decay works correctly for subsequent days,
                    # but do not touch purchase_count or cumulative_net_revenue (those
                    # reflect the main horizon only).
                    c.retention_score = min(2.5, c.retention_score + 0.12 * c.retention_sensitivity)
                    c.last_purchase_day = val_day

    # --- Write CustomerLifetimeRow for every customer ---
    lifetime_rows = []
    for c in customers:
        actual_val_rev: float | None = (
            clv_validation_revenue[c.customer_id] if config.clv_validation_days > 0 else None
        )
        hr = horizon_net_revenue[c.customer_id]
        lifetime_rows.append(
            CustomerLifetimeRow(
                run_id=run_id,
                customer_id=c.customer_id,
                total_orders=horizon_orders[c.customer_id],
                total_net_revenue=hr,
                total_contribution_margin=horizon_cm[c.customer_id],
                days_active=horizon_days_active[c.customer_id],
                churned_day=c.churned_day,
                predicted_clv=c.predicted_clv if c.predicted_clv is not None else 0.0,
                actual_clv_validation_revenue=actual_val_rev,
            )
        )
    db.add_all(lifetime_rows)
    db.flush()

    run = db.get(SimulationRunRow, run_id)
    if run:
        run.status = "completed"
        run.completed_at = datetime.now(UTC)
    db.commit()


def create_run_record(db: Session, config: RunConfig) -> uuid.UUID:
    """Insert a pending run, store JSON parameters, commit, and return the new id."""
    run_id = uuid.uuid4()
    run = SimulationRunRow(
        id=run_id,
        status="pending",
        seed=config.seed,
        horizon_days=config.horizon_days,
        baseline_end_day=config.baseline_end_day,
        experiment_start_day=config.experiment_start_day,
        customer_count=config.customer_count,
        created_at=datetime.now(UTC),
    )
    db.add(run)
    db.add(RunParameterRow(run_id=run_id, config=config.to_json()))
    db.commit()
    db.refresh(run)
    return run_id
