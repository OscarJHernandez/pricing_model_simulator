# Causal inference on simulation data

This document ties **identification**, **estimands**, and **adjustment methods** to the pricing simulator’s schema and engine. The executable walkthrough is [`notebooks/07_causal_inference.ipynb`](../notebooks/07_causal_inference.ipynb) (requires PostgreSQL and `pip install -e ".[dev]"` for `statsmodels`, `scikit-learn`, and `econml`).

For pricing mechanics and the shared-draw incrementality construction, see [`docs/pricing-model.md`](pricing-model.md). For equations (conversion rollups, Wilson / z-test, Beta–binomial), see [`docs/mathematical-models.md`](mathematical-models.md) (including the causal estimands subsection). For API rollups aligned with the notebook’s RCT cross-check, see `GET /api/runs/{id}/experiment-inference` and [`app/services/stats/inference.py`](../app/services/stats/inference.py).

---

## 1. What is identified in an experiment run?

During the **experiment** phase, each active customer has a fixed assignment `control` or `variant` ([`assign_treatments`](../app/services/simulation/assignment.py), table `experiment_assignments`). Assignment is **independent** of baseline cohort traits at run start (Bernoulli with `treatment_split`).

**Stable unit treatment value (SUTVA):** Customers do not interact; one customer’s prices do not appear in another’s utility. **Consistency:** The observed purchase outcome on a given day is the outcome under the assigned arm’s price rule that day.

Under these assumptions, the **intent-to-treat (ITT) / average treatment effect (ATE)** of assignment on a customer-day outcome—e.g. purchase indicator \(Y \in \{0,1\}\) or net revenue—is identified as the simple contrast between arms in the experiment phase:

\[
\tau = \mathbb{E}[Y \mid Z=\text{variant}] - \mathbb{E}[Y \mid Z=\text{control}],
\]

where \(Z\) is realized assignment. The notebook also uses **cluster-robust** inference at the `customer_id` level because the same customer contributes multiple days.

**Caveat:** Arm-level rollups in [`load_experiment_arm_rollups`](../app/services/stats/inference.py) treat customer-days as independent Bernoulli trials for Wilson / z-test summaries; that is a **practical** variance model, not a hierarchical customer random effects model (see [`docs/mathematical-models.md`](mathematical-models.md) §10.2).

---

## 2. Cross-arm ATE vs incremental (excursion) estimand

The engine stores two related but **distinct** quantities on `daily_customer_outcomes`:

| Column | Meaning |
|--------|---------|
| `incremental_order` | Experiment phase, **variant** arm only: purchase under variant price and **not** under the **counterfactual control total** for the same basket, using one shared uniform draw (see [`docs/pricing-model.md`](pricing-model.md)). |
| `counterfactual_would_buy` | Same draw compared to control price probability on variant days; on **control** experiment days, code sets the counterfactual purchase probability equal to the factual one, so this field **matches** `purchased` (no cross-arm counterfactual there). |

The **rate of incremental orders** among variant customer-days is a **pricing-excursion** summary tied to the shared-draw construction. It is **not** required to equal the **cross-arm** ATE in conversion: control and variant arms pool different customers and different price paths.

---

## 3. Observational adjustment (semi-synthetic and toy DGP)

When treatment is **not** randomized, identification typically requires **unconfoundedness** (no unmeasured confounders given observed covariates \(X\)) and **overlap** (propensity scores bounded away from 0 and 1).

- **IPW / stabilized weights:** Reweight units so that, in expectation, covariate balance mimics a randomized experiment for the contrast of interest.
- **Doubly robust (AIPW):** Combines a propensity model \(e(X)\) and an outcome regression \(m(z,X)\); consistency if **either** nuisance model is correctly specified (subject to regularity).

The notebook includes:

1. A **small closed-form DGP** where the true ATE is known and IPW / hand-built AIPW / `econml` DR learners recover it under stated assumptions.
2. A **pricing panel** with an **injected** pseudo-treatment correlated with customer traits, where the **RCT contrast** on true assignment remains the internal benchmark. Naive contrasts are biased; adjusted estimators are interpreted **carefully** (recovery to the RCT benchmark is not automatic unless the semi-synthetic design satisfies the same identifying assumptions as the toy block).

**Sensitivity:** Overlap failure (extreme propensities) inflates weights and destabilizes IPW/DR; the notebook shows **trimming** and propensity **overlap** plots.

---

## 4. Column and table map

| Concept | Primary persistence |
|--------|----------------------|
| Assignment \(Z\) | `experiment_assignments.treatment` |
| Phase / arm on outcomes | `daily_customer_outcomes.phase`, `.treatment` |
| Purchase, revenue | `.purchased`, `.net_revenue`, … |
| Shared-draw fields | `.incremental_order`, `.counterfactual_would_buy` |
| Covariates | `customers` (`segment`, `basket_mean`, `buy_propensity`, `location_zone`, …) |
| Arm rollups (API path) | `daily_aggregates` experiment phase, `location_zone = '__all__'` |

---

## 5. Extensions (not implemented here)

Instrumental variables, regression discontinuity, diff-in-diff across platforms, and sensitivity analysis for **unobserved** confounding (e.g. Rosenbaum bounds) are natural follow-ons. The simulator is a **sandbox**; external validity to live marketplace data is not claimed.
