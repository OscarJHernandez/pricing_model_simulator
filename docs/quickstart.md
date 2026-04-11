# Quick orientation

This repository is a **stochastic, customer-level pricing simulator**: virtual customers get traits and budgets, each simulation **day** updates churn and purchase decisions under **baseline** then **experiment** pricing, and results land in **PostgreSQL** with a **React** workbench for exploration. The Python `app` package is shared by the API, the engine, and the notebooks—there is no duplicate simulation logic in notebooks.

Use this page to pick a **first-hour path**. Step-by-step install commands, Docker notes, and troubleshooting live in the root [README.md](../README.md).

---

## Choose your path

### I want charts in the browser

Follow the **[5-minute quickstart](../README.md#5-minute-quickstart)** in the README: Postgres (Docker), Python venv, `pip install -e ".[dev]"`, `.env` on **port 5433**, migrations, Uvicorn + `npm run dev`, then **Scenario builder** → wait for completion → **Results**.

### I want numbers in the terminal

With the API and database running, from the repo root (venv active):

```bash
python scripts/quick_analysis.py
```

See [README — Quick analysis](../README.md#quick-analysis-one-command) for flags (`--seed`, `--customers`, etc.).

### I want to understand the model, then run simulations

1. Open [`notebooks/01_model_reference.ipynb`](../notebooks/01_model_reference.ipynb) (no database).
2. For a full run against the DB: [`02_simulation_and_metrics.ipynb`](../notebooks/02_simulation_and_metrics.ipynb), then [`03_ab_and_clv.ipynb`](../notebooks/03_ab_and_clv.ipynb).

Notebook setup and order are documented in [`notebooks/README.md`](../notebooks/README.md).

### I want batch runs and statistical inference

- **Notebooks:** [`04_statistical_inference.ipynb`](../notebooks/04_statistical_inference.ipynb) (Wilson + z-test; mostly no DB) and [`05_bayesian_experiment_inference.ipynb`](../notebooks/05_bayesian_experiment_inference.ipynb) (runs a short sim against PostgreSQL, then Beta–binomial comparison on real `daily_aggregates` rollups; same helpers as the API). For **causal inference** on customer-day outcomes (RCT, IPW/doubly robust, `econml`), use [`07_causal_inference.ipynb`](../notebooks/07_causal_inference.ipynb) and read [`causal-inference.md`](causal-inference.md).
- **API:** `POST /api/runs/batch` (same config, multiple seeds) and `GET /api/runs/{id}/experiment-inference` on a **completed** run (optional `prior_alpha`, `prior_beta`; response includes a `bayesian` block).
- **CLI:** [`scripts/run_batch_seeds.py`](../scripts/run_batch_seeds.py) for synchronous multi-seed runs against your database.

API tables and paths are in the README [API overview](../README.md#api-overview).

---

## Where to read next

| Document | Purpose |
|----------|---------|
| [`docs/pricing-model.md`](pricing-model.md) | How basket, fees, promos, and purchase probability are implemented |
| [`docs/mathematical-models.md`](mathematical-models.md) | Equations for CLV, demand, churn, cohort sampling, Wilson / z-test / Bayesian Beta–binomial |
| [`pricing_simulator_tech_spec_concise_v4.txt`](../pricing_simulator_tech_spec_concise_v4.txt) | Product spec and acceptance criteria |
| [`docs/spec-mapping.md`](spec-mapping.md) | Spec v4 vs this codebase (API prefix, washout, JSONB metrics, batch, inference) |
| [`AGENTS.md`](../AGENTS.md) | Stack, commands, layout, CLV model notes, deployment — for contributors and tooling |
