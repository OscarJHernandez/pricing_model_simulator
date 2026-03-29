# Pricing Simulator

A **learning and validation** web app that simulates **customer-level pricing** over many virtual days. Customers are generated with random traits, prices follow baseline and experiment policies (for example different delivery fees), purchases are **probabilistic**, and results are stored in **PostgreSQL** and shown in a **React workbench** UI.

The full product requirements live in [`pricing_simulator_tech_spec_concise_v4.txt`](pricing_simulator_tech_spec_concise_v4.txt). Day-to-day commands and conventions for contributors (including AI assistants) are in [`Agents.md`](Agents.md).

---

## 5-minute quickstart

If you already have **Docker** (for Postgres), **Python 3.11+**, and **Node**, run this checklist from the repo root:

- [ ] **1.** `docker compose up -d`
- [ ] **2.** `python3 -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
- [ ] **3.** `pip install -e ".[dev]"`
- [ ] **4.** `cp .env.example .env` — default URL uses **`localhost:5433`** (Docker Postgres). If you already had a `.env` with port **5432**, update it or you may hit the wrong server and see `role "pricing" does not exist`.
- [ ] **5.** `alembic upgrade head`
- [ ] **6.** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- [ ] **7.** In a second terminal: `cd frontend && npm install && npm run dev`
- [ ] **8.** Open the URL Vite prints (usually `http://localhost:5173`), submit **Scenario builder**, wait for the run to finish, then open **Results**.

**Verify:** `curl -s http://127.0.0.1:8000/api/health` should return JSON with `"status":"ok"`.

For explanations, troubleshooting, and options without Docker, see [Getting started (local development)](#getting-started-local-development) below.

---

## What you get

- **Backend:** Python, **FastAPI**, **SQLAlchemy**, **Alembic**, **PostgreSQL** (via psycopg3). One simulation **step = one day**; default horizon is **90 days** with a **baseline** phase then an **experiment** phase.
- **Frontend:** **Vite**, **React**, **TypeScript**, **Recharts** — left sidebar workbench: scenario builder, run summary, charts, customer explorer, validation notes.
- **Customer lifetime revenue model:** explicit daily **churn** dropout (retention-score-driven hazard), per-customer cumulative revenue tracking, **predictive CLV** using a discounted geometric-survival series, and an optional **holdout validation window** that re-runs the engine for extra days at baseline pricing so you can compare predicted vs actual.
- **Notebooks:** Four Jupyter notebooks under `notebooks/` import the **same** `app` package as the API (no duplicate simulation logic).
- **Deploy:** Example **Render** Blueprint in [`render.yaml`](render.yaml); start script runs migrations then Uvicorn.

---

## Prerequisites

| Tool | Why |
|------|-----|
| **Python 3.11+** | Backend and notebooks |
| **Node.js 20+** (or current LTS) | Frontend build and dev server |
| **PostgreSQL 16** (or compatible) | Required database (local Docker or hosted) |
| **Docker** (optional) | Easiest way to run Postgres locally via `docker compose` |

---

## Getting started (local development)

Do these steps **from the repository root** unless noted.

### 1. Clone and enter the project

```bash
cd pricing_model_simulator
```

### 2. Python virtual environment

Always use a project venv; do not install into system Python.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install the Python package

- **API only:** `pip install -e .`
- **API + Jupyter + pytest (recommended for notebooks):** `pip install -e ".[dev]"`

You can also install pinned dependencies with `pip install -r requirements.txt`, then `pip install -e .` or `pip install -e ".[dev]"` so the `app` package is importable.

### 4. Start PostgreSQL

**Option A — Docker (matches `.env.example`):**

```bash
docker compose up -d
```

The **`-d`** flag runs the database in the **background** so it keeps running after the command returns. If you run **`docker compose up`** without `-d`, Docker streams Postgres logs to your terminal and **Ctrl+C stops the container**—that is why you may see “Gracefully stopping…” and lose the database until you start it again.

This setup exposes Postgres on host port **5433**. Logs that say **“listening on … port 5432”** refer to the **inside** of the container only; from your Mac, connect with **`localhost:5433`** in `DATABASE_URL`.

If you see **“Skipping initialization”**, Docker reused an existing data volume from an earlier run (normal). The `pricing` user was created on the first successful init.

**Useful commands:** `docker compose ps` (is it running?), `docker compose logs -f db` (follow logs), `docker compose down` (stop and remove containers; add `-v` only if you want to wipe data).

**Option B — Your own Postgres:** Create a database and user, then set `DATABASE_URL` in `.env` to match that server (user, password, port—often `5432` and your OS username, not `pricing`).

### 5. Environment variables

```bash
cp .env.example .env
```

Edit `.env` if your database URL differs. Important variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL; with compose: `postgresql+psycopg://pricing:pricing@localhost:5433/pricing_simulator` |
| `CORS_ORIGINS` | Comma-separated browser origins for the API (dev: `http://localhost:5173`) |
| `STATIC_DIR` | Optional. If set to `frontend/dist`, the API can serve the built SPA (production-style) |

The app accepts Render-style `postgresql://` URLs and normalizes them for psycopg automatically.

### 6. Database migrations

With venv active and `DATABASE_URL` pointing at a live Postgres:

```bash
alembic upgrade head
```

### 7. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API base (with routes): `http://127.0.0.1:8000/api/...`
- Health check: `http://127.0.0.1:8000/api/health`

### 8. Run the frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`). The dev server **proxies `/api`** to `http://127.0.0.1:8000`, so the UI talks to the backend without CORS issues.

### 9. Use the UI

1. In **Scenario builder**, set seed, horizon, baseline/experiment days, customer count, pricing and promo options, then **Start simulation**.
2. You are sent to the **run summary**; the app polls until status is **completed** (or **failed**).
3. Open **Results** or **Customers** from the run navigation for charts and sampled customers.

---

## Production-style: API serves the built SPA

Build the frontend, then point the API at the build output:

```bash
cd frontend
npm run build
cd ..
```

In `.env`:

```env
STATIC_DIR=frontend/dist
```

Start Uvicorn (no need for a separate static host for a single-domain deploy):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API is still under `/api`; other paths serve the React app when `STATIC_DIR` is set.

---

## API overview

All JSON routes are under **`/api`**.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/runs` | Create a run (body = run config); returns `202` and runs simulation in the background |
| `GET` | `/api/runs` | List recent runs |
| `GET` | `/api/runs/{id}` | Run metadata + stored parameters |
| `GET` | `/api/runs/{id}/daily` | Daily aggregate rows (metrics JSON per segment) |
| `GET` | `/api/runs/{id}/customers` | Sampled customer traits |
| `GET` | `/api/runs/{id}/treatments` | Per-customer experiment assignment |
| `GET` | `/api/runs/{id}/outcomes/sample` | Sample of per-customer daily outcomes |
| `GET` | `/api/runs/{id}/customer-ltv` | Per-customer lifetime revenue: realized stats, predicted CLV, holdout validation revenue. Optional `?location_zone=A` filter. |

Run configuration fields match [`app/schemas/run_config.py`](app/schemas/run_config.py) (Pydantic), which is what the scenario form submits.

---

## Quick analysis (one command)

Once the API is running, the fastest way to kick off a simulation and see all the key results is:

```bash
source .venv/bin/activate
python scripts/quick_analysis.py
```

This runs a 500-customer, 90-day simulation with a 30-day CLV validation window, then prints:

- Phase-level P&L (baseline vs experiment)
- Experiment arm breakdown (control vs variant — orders, revenue, margin, incrementality)
- CLV calibration: mean predicted vs actual, RMSE, MAE, mean relative bias
- The 5 earliest-churning customers
- Exact curl commands and notebook pointers for going deeper

Options: `--seed N`, `--customers N`, `--horizon N`, `--clv-validation-days N`.

---

## Notebooks

From the **repo root**, with venv active and `pip install -e .` (or `.[dev]`):

```bash
jupyter lab
```

Open files in `notebooks/`. See [`notebooks/README.md`](notebooks/README.md) for full setup instructions and a changelog of recent model fixes.

### Walkthrough (start here — run in order)

| Notebook | Sections | Purpose | Needs DB? |
|----------|----------|---------|-----------|
| `01_model_reference.ipynb` | §0–§5 | **Start here.** Statistical model layer: RunConfig parameters, cohort distributions, purchase probability formula, temporal/geographic multipliers, promo eligibility. | No |
| `02_simulation_and_metrics.ipynb` | §6–§9 | Full simulation run, baseline vs experiment phase comparison, incrementality via shared-draw design, metric field reference. | **Yes** |
| `03_ab_and_clv.ipynb` | §10–§12 | A/B delivery fee sensitivity sweeps, customer journey traces, CLV validation (predicted vs actual). | **Yes** |

### Focused validation & analysis

| Notebook | Purpose | Needs DB? |
|----------|---------|-----------|
| `customer_model_validation.ipynb` | Unit-style assertions on `compute_purchase_probability` and Bernoulli sampling. Run after changes to `app/domain/customer.py`. | No |
| `repeat_purchase_validation.ipynb` | Multi-day behavioural loop validating retention score accumulation and decay. | No |
| `ab_test_analysis.ipynb` | Focused A/B experiment analysis — delivery fee sensitivity, incremental order lift, and revenue trade-off charts. | **Yes** |

Notebooks that run the full engine require `DATABASE_URL` set to a live PostgreSQL instance with migrations applied (`alembic upgrade head`).

---

## Tests

```bash
source .venv/bin/activate
pytest tests/ -q
```

---

## Deploying (Render)

See [`render.yaml`](render.yaml) and the **Deployment** section in [`Agents.md`](Agents.md). Typical flow:

1. Link a **PostgreSQL** instance and set `DATABASE_URL` (or use the Blueprint database).
2. **Build:** install Python package, then `cd frontend && npm install && npm run build`.
3. **Start:** [`scripts/start.sh`](scripts/start.sh) runs `alembic upgrade head` then Uvicorn on `$PORT`.
4. Set `STATIC_DIR=frontend/dist` and `CORS_ORIGINS` if the frontend is on another origin.

If your host’s Python build image does not include **Node**, build the frontend in CI and deploy the `frontend/dist` folder, or use a Docker-based deploy.

---

## Repository layout (short)

| Path | Role |
|------|------|
| `app/` | FastAPI app, models, domain `Customer`, simulation engine, pricing/metrics |
| `app/domain/customer.py` | `Customer` dataclass — purchase probability, churn, predictive CLV |
| `app/models/customer_lifetime.py` | ORM table for per-customer lifetime stats and CLV |
| `app/services/simulation/engine.py` | Daily loop — churn, purchases, CLV snapshot, validation extension |
| `app/schemas/run_config.py` | Pydantic run config — includes CLV fields (`churn_base_rate`, `clv_projected_days`, etc.) |
| `alembic/` | Migration environment and versions |
| `frontend/` | React workbench |
| `notebooks/` | `simulation_walkthrough.ipynb` (§0–12 end-to-end), plus three focused validation/analysis notebooks |
| `tests/` | Pytest tests |
| `scripts/quick_analysis.py` | **One-command quickstart** — run a simulation and print P&L, CLV calibration, and next-steps |
| `scripts/start.sh` | Migrate + Uvicorn (good for Render) |
| `docker-compose.yml` | Local Postgres |

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| `role "pricing" does not exist` | You are hitting a **different** Postgres than Docker Compose (often local Postgres on **5432** with your macOS username, not `pricing`). Fix: run `docker compose up -d`, set `DATABASE_URL` to **`localhost:5433`** as in `.env.example`, then `alembic upgrade head`. Or point `DATABASE_URL` at your real user/password on port 5432. |
| connection refused | Postgres not running, or wrong host/port in `DATABASE_URL` |
| Alembic errors | `DATABASE_URL` set, database reachable, `alembic upgrade head` from project root |
| UI cannot reach API | API running on 8000; use `npm run dev` so `/api` is proxied; or set `CORS_ORIGINS` if calling from another origin |
| Empty or stuck run | Check run status in UI; inspect API logs; failed runs store a truncated traceback on the run row |

---

## Documentation index

- **[`pricing_simulator_tech_spec_concise_v4.txt`](pricing_simulator_tech_spec_concise_v4.txt)** — product spec and acceptance criteria  
- **[`Agents.md`](Agents.md)** — contributor/agent guide, conventions, non-negotiables  
- **[`.env.example`](.env.example)** — environment template  
