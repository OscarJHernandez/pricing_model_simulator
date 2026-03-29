# Notebooks

This folder contains Jupyter notebooks for exploring, validating, and analysing the pricing simulator. All notebooks import `app` modules directly — there is no duplicate simulation logic.

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

These three notebooks replace the previous monolithic `simulation_walkthrough.ipynb` and cover the same material in focused, independently runnable parts.

| Notebook | Sections | Needs DB? | Description |
|----------|----------|-----------|-------------|
| [`01_model_reference.ipynb`](01_model_reference.ipynb) | §0–§5 | No | Statistical model layer: RunConfig parameters, cohort distributions, purchase probability formula, temporal/geographic multipliers, promo eligibility gates |
| [`02_simulation_and_metrics.ipynb`](02_simulation_and_metrics.ipynb) | §6–§9 | **Yes** | Running a full simulation, comparing baseline and experiment phases, incrementality via the shared-draw design, and a full metric field reference |
| [`03_ab_and_clv.ipynb`](03_ab_and_clv.ipynb) | §10–§12 | **Yes** | A/B delivery fee sensitivity sweeps, per-customer journey traces, and CLV validation (predicted vs actual revenue scatter and calibration) |

**Recommended execution order:** `01` → `02` → `03`. Notebooks 02 and 03 are independent of each other but both depend on having at least one completed run in the database.

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
