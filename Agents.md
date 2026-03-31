# Agents guide — Pricing Simulator

This repository implements the MVP described in `pricing_simulator_tech_spec_concise_v4.txt`: a stochastic, customer-level pricing simulator with baseline and experiment phases, PostgreSQL persistence, FastAPI, a React workbench UI, and validation notebooks.

**Orientation (any reader):** [`README.md`](README.md) has the 5-minute checklist and full local setup. [`docs/quickstart.md`](docs/quickstart.md) is a short “choose your path” guide (UI vs CLI vs notebooks vs batch/inference). [`docs/pricing-model.md`](docs/pricing-model.md) explains how basket, fees, promos, and purchase probability are implemented. [`docs/mathematical-models.md`](docs/mathematical-models.md) states the same models in equation form (CLV, demand, churn, cohort draws, Wilson / z-test, Beta–binomial Bayesian inference). Spec deltas vs code: [`docs/spec-mapping.md`](docs/spec-mapping.md).

## Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, SQLAlchemy 2, Alembic, PostgreSQL (psycopg3), NumPy/Pandas  
- **Frontend:** Vite, React, TypeScript, Recharts, React Router  
- **Deploy:** Render (Blueprint `render.yaml`) with managed PostgreSQL  

## Setup

1. Create and activate a virtual environment in the project root:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the app (includes API dependencies; optional `[dev]` adds Jupyter, pytest, httpx):

   ```bash
   pip install -e ".[dev]"
   ```

3. Start PostgreSQL (example with Docker). Compose maps Postgres to host port **5433** so it does not clash with a local Postgres on **5432**.

   ```bash
   docker compose up -d
   ```

4. Copy `.env.example` to `.env` and adjust `DATABASE_URL` if needed (defaults to `localhost:5433` with user `pricing`).

5. Run migrations:

   ```bash
   alembic upgrade head
   ```

6. Frontend dependencies:

   ```bash
   cd frontend && npm install
   ```

## Run commands

- **API (dev):** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`  
- **Frontend (dev):** `cd frontend && npm run dev` — Vite proxies `/api` to `http://127.0.0.1:8000`  
- **Production-style API + built UI:** build the frontend (`cd frontend && npm run build`), set `STATIC_DIR=frontend/dist` in `.env`, then start Uvicorn as above  
- **Migrations:** `alembic revision --autogenerate -m "message"` (when models change) then `alembic upgrade head`  
- **Quick analysis (recommended first run):** `python scripts/quick_analysis.py` — runs a full simulation and prints P&L, CLV calibration, and next-step pointers. Accepts `--seed N`, `--customers N`, `--horizon N`, `--clv-validation-days N`.  
- **Notebooks:** from repo root with venv active and `pip install -e .`, open files under `notebooks/` in Jupyter. Start with `01_model_reference.ipynb` → `02_simulation_and_metrics.ipynb` → `03_ab_and_clv.ipynb` → `04_statistical_inference.ipynb` → `05_bayesian_experiment_inference.ipynb` → `06_executive_pricing_experiment.ipynb` (capstone). See `notebooks/README.md` for full instructions.

## Notebook roles

| Notebook | Role |
|----------|------|
| `01_model_reference.ipynb` | **Model reference (Part 1)** — §0–5: RunConfig parameters, cohort distributions, purchase probability formula, temporal/geo multipliers, promo eligibility. No database needed. |
| `02_simulation_and_metrics.ipynb` | **Simulation run (Part 2)** — §6–9: full simulation run, baseline vs experiment phase comparison, incrementality via shared-draw design, metric field reference. Requires PostgreSQL. |
| `03_ab_and_clv.ipynb` | **Analysis & CLV (Part 3)** — §10–12: A/B delivery fee sensitivity sweeps, customer journey traces, CLV validation (predicted vs actual). Requires PostgreSQL. |
| `04_statistical_inference.ipynb` | **Inference (spec §9)** — Wilson CIs, two-proportion z-test via `app/services/stats/inference.py`; complements `GET /api/runs/{id}/experiment-inference` and batch seeds. Mostly no DB. |
| `05_bayesian_experiment_inference.ipynb` | **Bayesian inference** — runs a short sim, loads `daily_aggregates` via `load_experiment_arm_rollups` (same as API); frequentist vs Beta–binomial; uniform vs Jeffreys. Requires PostgreSQL. |
| `06_executive_pricing_experiment.ipynb` | **Capstone** — end-to-end experiment design, multi-seed sweep, primary run with CLV holdout, aggregates, `build_experiment_inference`, CLV vs OLS benchmark, dynamic-pricing guide, executive summary. Requires PostgreSQL. |
| `customer_model_validation.ipynb` | **Regression test** — assertion-based validation of `compute_purchase_probability` and Bernoulli draws. No database needed. Run after changes to `app/domain/customer.py`. |
| `repeat_purchase_validation.ipynb` | **Behavioural test** — multi-day loop verifying retention score accumulation and decay. No database needed. Run after changes to retention logic. |
| `ab_test_analysis.ipynb` | **Experiment analysis** — delivery fee sensitivity, incremental lift, and revenue trade-off charts across multiple A/B runs. Requires PostgreSQL. |

All notebooks import `app` modules directly (no duplicate logic). They share the same `DATABASE_URL` env var as the API when a live database is needed.  

## Code quality (Python)

With `pip install -e ".[dev]"` you get **Ruff** (lint + format) and **Mypy** (types, with the SQLAlchemy plugin). From the repo root:

- **Lint:** `ruff check app tests`
- **Format:** `ruff format app tests` (check-only: `ruff format app tests --check`)
- **Types:** `mypy app tests`
- **Tests:** `pytest tests` — includes `tests/test_notebooks_execute.py`, which executes all files under `notebooks/` (requires PostgreSQL + migrations; set `SKIP_NOTEBOOK_TESTS=1` to skip).

Alembic revision files under `alembic/versions/` are excluded from Ruff/Mypy to keep migration noise low.

## Layout

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app, CORS, optional static SPA mount |
| `app/api/routes/` | HTTP API (`/api/runs`, …) |
| `app/models/` | SQLAlchemy ORM tables |
| `app/models/customer_lifetime.py` | `CustomerLifetimeRow` — per-customer lifetime stats, predicted CLV, holdout validation revenue |
| `app/domain/customer.py` | In-memory `Customer` — purchase probability, churn hazard, predictive CLV formula |
| `app/services/simulation/engine.py` | Daily loop: churn draws, purchase decisions, CLV snapshot, optional validation extension, persistence |
| `app/services/pricing/` | Policies, temporal/geo multipliers, promo rules |
| `app/services/metrics/` | Aggregate metric dicts |
| `app/schemas/run_config.py` | Pydantic run configuration (API + engine) — includes CLV fields |
| `app/schemas/day_metrics.py` | `DayMetrics` TypedDict for aggregate JSONB |
| `app/schemas/api_responses.py` | Pydantic response models for `/api/runs` — includes `CustomerLTVOut` |
| `notebooks/01_model_reference.ipynb` | §0–5 narrative: RunConfig, cohort distributions, purchase probability, temporal/geo context, promo eligibility (no DB) |
| `notebooks/02_simulation_and_metrics.ipynb` | §6–9 narrative: full simulation run, phase analysis, incrementality, metric field reference (requires DB) |
| `notebooks/03_ab_and_clv.ipynb` | §10–12 narrative: A/B comparison, customer journeys, CLV validation (requires DB) |
| `notebooks/04_statistical_inference.ipynb` | Spec §9 narrative: Wilson intervals, z-test, ties to batch API |
| `notebooks/05_bayesian_experiment_inference.ipynb` | Bayesian vs frequentist experiment inference; ties to `GET .../experiment-inference` |
| `notebooks/06_executive_pricing_experiment.ipynb` | Capstone: design, multi-seed sweep, CLV holdout, inference, OLS benchmark, ML/dynamic-pricing guide (requires DB) |
| `docs/spec-mapping.md` | Tech spec v4 vs implementation (API prefix, washout, JSONB metrics, batch/inference) |
| `docs/quickstart.md` | First-hour orientation: UI, `quick_analysis.py`, notebooks 01–04, batch/inference pointers |
| `docs/pricing-model.md` | Pricing and demand model: basket, phases, promos, purchase probability, incrementality |
| `docs/mathematical-models.md` | Formal equations: predictive CLV series, purchase probability factors, churn, cohort sampling, Wilson / z-test, Beta–binomial Bayesian summaries |
| `notebooks/customer_model_validation.ipynb` | Unit assertions on `compute_purchase_probability` and Bernoulli sampling |
| `notebooks/repeat_purchase_validation.ipynb` | Multi-day retention decay behavioural sanity check |
| `notebooks/ab_test_analysis.ipynb` | A/B experiment analysis and delivery fee sensitivity charts |
| `notebooks/README.md` | Execution instructions, notebook index, and model changelog |
| `frontend/` | React workbench |
| `alembic/versions/` | Schema migrations |
| `scripts/quick_analysis.py` | One-command quickstart: run a simulation and print P&L, CLV calibration, churn summary |
| `scripts/start.sh` | Render/local: migrate then Uvicorn |

## Non-negotiables (from product spec)

- One simulation step equals one day; default horizon 90 days (configurable).  
- Baseline phase precedes experiment; experiment does not start on day 1.  
- Each customer is a class instance with budget, buy propensity, price threshold, evolving state, and stochastic purchases.  
- Notebooks and API share the same Python modules (no parallel toy implementations).  
- Outputs include orders, revenue, margin, and incrementality-style metrics; temporal and geographic context apply; promo eligibility and campaign budget are enforced in code.  
- UI is a **left-aligned workbench** (sidebar + main panels), not a centered marketing layout.  
- Target deployment uses **PostgreSQL** (e.g. Render).  

## Customer lifetime revenue model

The CLV model lives entirely in `app/domain/customer.py` and `app/services/simulation/engine.py`. For how offered prices and demand multipliers are built before churn and CLV snapshots, see [`docs/pricing-model.md`](docs/pricing-model.md). For the CLV and churn formulas in notation, see [`docs/mathematical-models.md`](docs/mathematical-models.md). Key design decisions:

- **Churn hazard:** `p_churn = churn_base_rate × max(0, 2.0 − retention_score)`. At high retention (score ≥ 2.0) churn probability is zero; at the floor (score = 1.0) it equals `churn_base_rate`. Default 0.2%/day.  
- **Predictive CLV formula (discounted geometric survival):**  
  `CLV = daily_rev × s × (1 − s^N) / (1 − s)` where `s = (1 − p_churn) × (1 − r/365)` and `N = clv_projected_days`. Computed at end of horizon using each customer's own `basket_mean` as the basket subtotal (not the deprecated `baseline_order_price`).  
- **Holdout validation:** set `clv_validation_days > 0` in `RunConfig`. The engine runs that many extra days at baseline pricing (no experiment arms, no churn draws) and stores actual revenue per customer in `CustomerLifetimeRow.actual_clv_validation_revenue`. This is what §12 of the walkthrough notebook uses for the calibration charts.  
- **`customer_lifetime` table** stores: `total_orders`, `total_net_revenue`, `total_contribution_margin`, `days_active`, `churned_day`, `predicted_clv`, `actual_clv_validation_revenue`.  
- **API:** `GET /api/runs/{id}/customer-ltv` with optional `?location_zone=` filter.  

`RunConfig` CLV fields (all optional, safe defaults):

| Field | Default | Meaning |
|-------|---------|---------|
| `churn_base_rate` | `0.002` | Daily churn hazard at floor retention |
| `clv_projected_days` | `90` | Forward horizon for predictive CLV |
| `discount_rate_annual` | `0.10` | Annual discount rate for DCF |
| `clv_validation_days` | `0` | Extra days run after horizon to collect actuals (0 = disabled) |

## Conventions

- New HTTP handlers go under `app/api/routes/` and stay thin; simulation logic stays in `app/services/`.  
- Schema changes: update ORM models, add an Alembic revision, keep `alembic/env.py` imports and `app/models/__init__.py` in sync with models.  
- `DATABASE_URL` on hosts that expose `postgresql://` is normalized to `postgresql+psycopg://` in `app/db/session.py` and `alembic/env.py`.  
- CLV validation days are **not** written to `daily_aggregate` or `daily_customer_outcomes` — they exist solely for CLV calibration. Do not add logging or aggregate writes inside the validation extension loop.  

## Deployment (Render)

- Use `render.yaml` or create a **Python** web service with root directory set to the repo.  
- **Build:** `pip install . && cd frontend && npm install && npm run build` (requires Node on the build image).  
- **Start:** `sh scripts/start.sh` (runs `alembic upgrade head` then Uvicorn on `$PORT`).  
- Link a **PostgreSQL** instance; set `DATABASE_URL` from the dashboard if not using a Blueprint.  
- Set `CORS_ORIGINS` to your deployed frontend origin if the UI is hosted separately; for a single service with `STATIC_DIR=frontend/dist`, same-origin requests need no CORS for the SPA.  
- If the Python build image lacks Node, build the frontend in CI and deploy artifacts, or switch to a Docker-based deploy.  

## Cursor / AI tooling

Some tools look for `AGENTS.md` (uppercase). This project uses **`Agents.md`** at the repo root; symlink or duplicate if your workflow expects the other name.
