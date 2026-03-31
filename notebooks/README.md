# Notebooks

This folder contains Jupyter notebooks for exploring, validating, and analysing the pricing simulator. All notebooks import `app` modules directly — there is no duplicate simulation logic.

**New to the repo?** See [`../docs/quickstart.md`](../docs/quickstart.md) for UI vs CLI vs notebook paths. For a concise description of basket totals, fees, promos, purchase probability, and experiment phases, see [`../docs/pricing-model.md`](../docs/pricing-model.md). For the same models in equation form (CLV, churn, cohort sampling, inference), see [`../docs/mathematical-models.md`](../docs/mathematical-models.md). For identification, incrementality vs ATE, and adjustment methods, see [`../docs/causal-inference.md`](../docs/causal-inference.md) (pairs with `07_causal_inference.ipynb`).

**Authoring / editing notebooks:** Standards (motivation blocks, key insights, widgets, notation) live in [`SKILL_notebook_quality.md`](SKILL_notebook_quality.md).

---

## Prerequisites

From the **repo root**, with your virtual environment active:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # installs Jupyter, pytest, and the app package
```

Start Jupyter:

```bash
jupyter lab                        # or: jupyter notebook
```

Open files from the `notebooks/` directory.

---

## PostgreSQL setup (required for §6 onward)

Notebooks that run the simulation engine write to and read from PostgreSQL.

```bash
# 1. Start Postgres (Docker is the easiest path)
docker compose up -d

# 2. Copy environment file and confirm DATABASE_URL
cp .env.example .env               # default points to localhost:5433

# 3. Apply migrations
alembic upgrade head
```

Set `DATABASE_URL` in `.env` (or export it in your shell) before launching Jupyter.
The setup cell in each DB-required notebook will load `.env` automatically via `python-dotenv`.

---

## Walkthrough notebooks (start here)

These notebooks replace the previous monolithic `simulation_walkthrough.ipynb` and cover the model, simulation, A/B + CLV, and statistical inference.

| Notebook | Sections | Needs DB? | Description |
|----------|----------|-----------|-------------|
| [`01_model_reference.ipynb`](01_model_reference.ipynb) | §0–§5 | No | Statistical model layer: RunConfig parameters, cohort distributions, purchase probability formula, temporal/geographic multipliers, promo eligibility gates, segment labels |
| [`02_simulation_and_metrics.ipynb`](02_simulation_and_metrics.ipynb) | §6–§9 | **Yes** | Full simulation run, baseline / washout / experiment phases, incrementality, metric glossary (JSONB vs written spec, `active_customers_evaluated`), outcome column samples, dashboard-style revenue plots |
| [`03_ab_and_clv.ipynb`](03_ab_and_clv.ipynb) | §10–§12 | **Yes** | A/B delivery fee sensitivity sweeps, per-customer journey traces, CLV validation, segment field note |
| [`04_statistical_inference.ipynb`](04_statistical_inference.ipynb) | Spec §9 | No* | Wilson intervals and two-proportion z-test using `app/services/stats/inference.py` (same logic as `GET /api/runs/{id}/experiment-inference`); multi-seed batch via API or `scripts/run_batch_seeds.py` |
| [`05_bayesian_experiment_inference.ipynb`](05_bayesian_experiment_inference.ipynb) | Inference | **Yes** | Runs a short simulation, loads experiment rollups via `load_experiment_arm_rollups` (same as the API), then frequentist vs Bayesian comparison + appendix toy counts; see `docs/mathematical-models.md` §10.3 |
| [`06_executive_pricing_experiment.ipynb`](06_executive_pricing_experiment.ipynb) | Capstone | **Yes** | End-to-end narrative: `RunConfig` design, multi-seed variability, primary run with CLV holdout, aggregates, inference (`build_experiment_inference`), CLV calibration vs OLS benchmark, dynamic-pricing guide, executive summary |
| [`07_causal_inference.ipynb`](07_causal_inference.ipynb) | Causal inference | **Yes** | RCT identification, cluster-robust OLS/Logit, `build_experiment_inference` cross-check, oracle (`incremental_order` / `counterfactual_would_buy`), 8-seed ATE benchmark, toy DGP (IPW, hand AIPW, `LinearDRLearner` / `ForestDRLearner`), semi-synthetic confounded pseudo-treatment with overlap plots + trimmed IPW, `ForestDRLearner` HTE by segment. Uses `scikit-learn` and `econml` (`pip install -e ".[dev]"`). Runtime is higher than notebook `05` (multiple full runs + forests). |

\*Pure-math cells need no DB; comparing to a live run requires PostgreSQL like notebook 02.

**Recommended execution order:** `01` → `02` → `03` → `04` → `05` → `06` → `07`. Notebook `03` includes a database setup cell and bootstraps `run_id` / `cfg_main` from the §10 A/B run so it can execute standalone when PostgreSQL is available (running after `02` is still fine). Notebooks `06` and `07` are standalone (each imports DB + runs its own simulations).

**CI:** `pytest tests/test_notebooks_execute.py` runs every notebook in this folder (see root README / `Agents.md`); use `SKIP_NOTEBOOK_TESTS=1` to skip locally without Postgres.

---

## Focused validation notebooks

| Notebook | Needs DB? | When to run |
|----------|-----------|-------------|
| [`customer_model_validation.ipynb`](customer_model_validation.ipynb) | No | After changes to `app/domain/customer.py` — assertion-based regression test for `compute_purchase_probability` and Bernoulli sampling |
| [`repeat_purchase_validation.ipynb`](repeat_purchase_validation.ipynb) | No | After changes to retention logic — multi-day loop verifying score accumulation and decay |
| [`ab_test_analysis.ipynb`](ab_test_analysis.ipynb) | **Yes** | Focused A/B experiment analysis: delivery fee lift, incremental orders, revenue trade-off charts across multiple runs |

---

## Key model changes (recent)

The following fixes and improvements have been applied to the simulation since earlier versions of the walkthrough:

- **Promo demand haircut scoped to variant arm only.** The 0.85 propensity multiplier for promo-ineligible customers now applies only to variant arm customers during the experiment phase. Control and baseline customers are not affected.
- **Predictive CLV uses per-customer basket mean.** Each customer's `basket_mean` is used as the basket subtotal when computing predictive CLV, replacing the global (and legacy) `baseline_order_price` constant.
- **Contribution margin tracked accurately.** `CustomerLifetimeRow.total_contribution_margin` now reflects the sum of per-order `net_revenue - variable_cost_rate × basket`, not the post-hoc approximation `net_revenue × (1 - cost_rate)`.
- **Washout phase label.** Days between `baseline_end_day` and `experiment_start_day` are now labelled `"washout"` in aggregates and outcomes, making the data correct when the two config fields differ by more than one.
- **Configurable treatment split.** `RunConfig.treatment_split` (default 0.5) controls the variant fraction; no longer hardcoded to 50/50.
- **Acquisition channel wired into propensity.** Channel modifiers (`organic`: 1.0, `paid`: 0.85, `referral`: 1.15 by default) now multiply `buy_propensity` at cohort generation time; override via `channel_propensity_modifiers` in `RunConfig`.
