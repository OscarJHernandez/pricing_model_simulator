# Pricing and demand model

This document describes how **customer-facing prices** are built in each simulation day and how those prices feed the **stochastic purchase** decision. It matches the implementation in the simulation engine and domain layer, not a reprint of the full product spec. For the same content in **equation form** (CLV series, purchase probability, churn, cohort sampling, Wilson intervals, z-test), see [`docs/mathematical-models.md`](mathematical-models.md).

---

## Scope

The simulator generates a cohort of synthetic **customers** ([`Customer`](../app/domain/customer.py)). Each **day** is one step: optional churn draw, then for each active customer a **basket subtotal** is drawn, **fees and discounts** are applied to produce an **offered total price**, and the customer **buys with probability** \(p\) computed from that price and context, then a single **Bernoulli** draw ([`decide_purchase`](../app/domain/customer.py)) decides whether an order happens.

**Basket vs fixed order price:** Totals are always based on a per-customer random basket. The field `baseline_order_price` on [`RunConfig`](../app/schemas/run_config.py) is **deprecated** and not used on the live pricing path ([`docs/spec-mapping.md`](spec-mapping.md)). Basket sampling and price assembly live in [`_sample_basket`](../app/services/simulation/engine.py) and [`_price_breakdown`](../app/services/simulation/engine.py).

---

## How the customer-facing price is computed

For a given day, the engine samples a **basket subtotal** \(B\) from a **lognormal** distribution centered on `Customer.basket_mean` with fixed log-scale volatility (`0.25` in [`_sample_basket`](../app/services/simulation/engine.py)), then floors at a small minimum.

The **offered total** is built in [`_price_breakdown`](../app/services/simulation/engine.py) from immutable policies ([`BaselinePolicy`](../app/services/pricing/policies.py), [`ExperimentArm`](../app/services/pricing/policies.py)):

1. **Delivery fee** for the active arm (baseline, control, or variant), except it is **waived** when \(B \geq\) `free_delivery_threshold` (threshold is defined on the baseline policy and reused in experiment arms).
2. **Service fee** from the baseline policy (same in experiment).
3. **Discounts:** subtract baseline `discount_amount`. For the **variant** arm only, if the customer is **promo-eligible** that day, also subtract the variant’s extra discount (`variant_extra_discount` in config); if not eligible, the extra discount is not applied.

**Washout and baseline phases** use baseline delivery fee and baseline discounts only (no experiment arm). **Experiment phase** uses the arm matching the customer’s assigned treatment (`control` or `variant`).

---

## Simulation phases

| Phase | Pricing | Notes |
|--------|---------|--------|
| **baseline** | Full [`BaselinePolicy`](../app/services/pricing/policies.py) | Days up to `baseline_end_day`. |
| **washout** | Same totals as baseline | Days after baseline through `experiment_start_day - 1`; no experiment arm pricing. See [spec mapping](spec-mapping.md). |
| **experiment** | Control vs variant [`ExperimentArm`](../app/services/pricing/policies.py) | From `experiment_start_day`; assignment from [`assign_treatments`](../app/services/simulation/assignment.py). Policy objects are built in [`_pricing_for_config`](../app/services/simulation/engine.py). |

---

## Purchase probability

[`Customer.compute_purchase_probability`](../app/domain/customer.py) maps an **offered total** and a [`PurchaseContext`](../app/domain/customer.py) to \(p \in [0, 1]\).

**Hard constraint:** If `offered_price > budget`, probability is **0**.

**Multiplicative structure (conceptually):**

- **Base appetite:** `buy_propensity` × `channel_propensity_modifier`.
- **Price vs threshold:** Softer penalty when the offer is near or below `price_threshold`; ratio is capped for stability.
- **New vs repeat:** First-time buyers use a term that depends on `promo_sensitivity`; repeat buyers get a lift from `repeat_boost` and purchase count.
- **Calendar:** `temporal_multiplier` × `geographic_multiplier` — from [`temporal_multiplier`](../app/services/pricing/temporal.py) (weekend vs weekday and mild seasonality) and [`zone_multiplier`](../app/services/pricing/geographic.py) (zone defaults and `RunConfig.zone_modifiers` overrides).
- **Promo ineligibility (variant only):** If the customer is on the **variant** arm during **experiment** but is **not** promo-eligible, the engine passes `promo_eligible=False` into context only in that case; the probability model applies an extra **0.85** factor on the calendar block. **Control**, **baseline**, and **washout** customers are treated as promo-eligible for this purpose so they do not get that haircut ([engine loop](../app/services/simulation/engine.py) setting `ctx_promo`).
- **Retention:** Mild lift from `retention_score` scaled by `retention_sensitivity`.

The result is clipped to \([0, 1]\). [`decide_purchase`](../app/domain/customer.py) draws uniform \(U\) and purchases if \(U < p\).

---

## Promo rules

Variant **extra** discount is gated by [`promo_eligible`](../app/services/pricing/promo.py) using [`PromoRules`](../app/services/pricing/promo.py) from run config:

- Optional **campaign budget** (cumulative discount spend).
- **First order only** (no extra discount after the customer has ordered before).
- **Max uses per customer** and **cooldown** after a promo use.

If eligible, the variant’s `discount_amount` is included in `_price_breakdown`; eligibility also drives the `PurchaseContext.promo_eligible` flag for variant customers as above.

---

## Incrementality (shared random draw)

For **experiment** customers on the **variant** arm, the engine evaluates purchase probability at both the **variant offered total** and a **counterfactual control-arm total** for the **same basket** (fourth return value of [`_price_breakdown`](../app/services/simulation/engine.py), documented there as `counterfactual_control`).

A **single** uniform draw \(U\) is compared to both probabilities: the customer **purchases** if \(U < p_{\text{variant}}\), and **counterfactual_would_buy** is true if \(U < p_{\text{control}}\). An order is flagged **incremental** when the variant draw yields a purchase but the counterfactual control draw would not ([`execute_simulation`](../app/services/simulation/engine.py)). This is a **shared randomness** design for incrementality-style metrics on outcomes.

---

## Related dynamics (short)

Pricing and demand interact with **lifecycle** state:

- **Churn:** Daily churn probability scales with `retention_score` ([`compute_churn_probability`](../app/domain/customer.py)); high retention can drive churn to zero.
- **After a purchase:** [`register_purchase`](../app/domain/customer.py) updates revenue, counts, and bumps `retention_score` (with cap); time since last purchase decays retention between orders.
- **Predictive CLV:** [`compute_predictive_clv`](../app/domain/customer.py) uses a discounted geometric-style series combining daily purchase probability (at a customer-specific typical price), churn, and discount rate. Tunable fields are on `RunConfig` (see [AGENTS.md](../AGENTS.md) and README for CLV defaults).

---

## Where to go deeper

| Resource | Role |
|----------|------|
| [docs/mathematical-models.md](mathematical-models.md) | Formal mathematics: predictive CLV, demand, churn, inference. |
| [docs/quickstart.md](quickstart.md) | First-hour orientation (UI, CLI, notebooks, batch/inference). |
| [notebooks/01_model_reference.ipynb](../notebooks/01_model_reference.ipynb) | Narrative walkthrough of parameters and formula (sections 0–5). |
| [app/schemas/run_config.py](../app/schemas/run_config.py) | All tunable fees, promo flags, horizon, phases, and CLV-related fields. |
| [docs/spec-mapping.md](spec-mapping.md) | Spec v4 vs implementation (API prefix, washout, JSONB metrics, deprecated fields). |
| [AGENTS.md](../AGENTS.md) | Contributor layout, CLV summary, deployment. |
| [app/services/simulation/engine.py](../app/services/simulation/engine.py) | Daily loop: basket, price breakdown, probability, purchase, persistence. |
