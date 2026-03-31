# Tech spec (v4) vs this implementation

Cross-reference for [`pricing_simulator_tech_spec_concise_v4.txt`](../pricing_simulator_tech_spec_concise_v4.txt).

For a reader-oriented description of the pricing and demand stack (lognormal basket, phase pricing, promo gates, purchase probability, shared-draw incrementality), see [`docs/pricing-model.md`](pricing-model.md). For formal notation (including predictive CLV and post-run Wilson / z-test / Beta–binomial Bayesian summaries), see [`docs/mathematical-models.md`](mathematical-models.md). First-hour setup paths: [`docs/quickstart.md`](quickstart.md).

## HTTP API prefix

The spec illustrates paths such as `GET /runs`. The app mounts the runs router at **`/api/runs`** (see `app/main.py`). Example: `GET /api/runs/{run_id}/daily`.

## Washout phase

Days strictly after `baseline_end_day` and before `experiment_start_day` use baseline pricing with no experiment arm pricing; aggregates and outcomes are labelled **`washout`**. This keeps a gap between “baseline learning” and “experiment live” when those config fields differ by more than one day.

## Daily aggregates storage

The spec lists flat columns on `daily_aggregates`. Here, numeric rollups live in a **`metrics` JSONB** column shaped like `DayMetrics` (`app/schemas/day_metrics.py`). The API returns the same keys as JSON (`DayMetricsOut`), plus **`active_customers_evaluated`**, an alias equal to **`customers_evaluated`** (non-churned customers evaluated that day in that slice).

## Pricing: basket vs fixed order price

`RunConfig.baseline_order_price` is **deprecated** and not used in the live pricing path. Basket subtotals are drawn from a lognormal around each customer’s `basket_mean`; fees and discounts are applied in `app/services/simulation/engine.py`.

## Statistical endpoints (spec section 9)

- **`POST /api/runs/batch`** — same configuration, multiple seeds (async background jobs).
- **`GET /api/runs/{run_id}/experiment-inference`** — pooled experiment-phase totals, Wilson intervals on conversion, two-proportion z-test, and a **Beta–binomial Bayesian** block (`prior_alpha`, `prior_beta` query params; see `app/services/stats/inference.py`).
- **CLI:** `scripts/run_batch_seeds.py` runs multiple seeds **synchronously** against your database.

## Customer segment and outcomes

`customers.segment` is set at cohort creation from budget, `price_threshold`, and `buy_propensity` (`derive_segment` in `app/domain/customer.py`). `daily_customer_outcomes` stores **`purchase_count_after_event`** and **`days_since_last_purchase`** per row for analysis exports.
