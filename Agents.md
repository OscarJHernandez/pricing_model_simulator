# Agents guide — Pricing Simulator

This repository implements the MVP described in `pricing_simulator_tech_spec_concise_v4.txt`: a stochastic, customer-level pricing simulator with baseline and experiment phases, PostgreSQL persistence, FastAPI, a React workbench UI, and validation notebooks.

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

3. Start PostgreSQL (example with Docker):

   ```bash
   docker compose up -d
   ```

4. Copy `.env.example` to `.env` and adjust `DATABASE_URL` if needed.

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
- **Notebooks:** from repo root with venv active and `pip install -e .`, open files under `notebooks/` in Jupyter  

## Layout

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app, CORS, optional static SPA mount |
| `app/api/routes/` | HTTP API (`/api/runs`, …) |
| `app/models/` | SQLAlchemy ORM tables |
| `app/domain/customer.py` | In-memory `Customer` used by the engine |
| `app/services/simulation/engine.py` | Daily loop, persistence of outcomes |
| `app/services/pricing/` | Policies, temporal/geo multipliers, promo rules |
| `app/services/metrics/` | Aggregate metric dicts |
| `app/schemas/run_config.py` | Pydantic run configuration (API + engine) |
| `notebooks/` | Validation notebooks (import `app`, no duplicate logic) |
| `frontend/` | React workbench |
| `alembic/versions/` | Schema migrations |
| `scripts/start.sh` | Render/local: migrate then Uvicorn |

## Non-negotiables (from product spec)

- One simulation step equals one day; default horizon 90 days (configurable).  
- Baseline phase precedes experiment; experiment does not start on day 1.  
- Each customer is a class instance with budget, buy propensity, price threshold, evolving state, and stochastic purchases.  
- Notebooks and API share the same Python modules (no parallel toy implementations).  
- Outputs include orders, revenue, margin, and incrementality-style metrics; temporal and geographic context apply; promo eligibility and campaign budget are enforced in code.  
- UI is a **left-aligned workbench** (sidebar + main panels), not a centered marketing layout.  
- Target deployment uses **PostgreSQL** (e.g. Render).  

## Conventions

- New HTTP handlers go under `app/api/routes/` and stay thin; simulation logic stays in `app/services/`.  
- Schema changes: update ORM models, add an Alembic revision, keep `alembic/env.py` imports in sync with models.  
- `DATABASE_URL` on hosts that expose `postgresql://` is normalized to `postgresql+psycopg://` in `app/db/session.py` and `alembic/env.py`.  

## Deployment (Render)

- Use `render.yaml` or create a **Python** web service with root directory set to the repo.  
- **Build:** `pip install . && cd frontend && npm install && npm run build` (requires Node on the build image).  
- **Start:** `sh scripts/start.sh` (runs `alembic upgrade head` then Uvicorn on `$PORT`).  
- Link a **PostgreSQL** instance; set `DATABASE_URL` from the dashboard if not using a Blueprint.  
- Set `CORS_ORIGINS` to your deployed frontend origin if the UI is hosted separately; for a single service with `STATIC_DIR=frontend/dist`, same-origin requests need no CORS for the SPA.  
- If the Python build image lacks Node, build the frontend in CI and deploy artifacts, or switch to a Docker-based deploy.  

## Cursor / AI tooling

Some tools look for `AGENTS.md` (uppercase). This project uses **`Agents.md`** at the repo root; symlink or duplicate if your workflow expects the other name.
