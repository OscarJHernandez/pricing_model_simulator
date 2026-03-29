"""Quick-start analysis script — run a simulation and print a full summary.

Usage (from repo root, venv active):

    python scripts/quick_analysis.py

No flags required.  DATABASE_URL is read from .env if present, otherwise the
docker-compose default (localhost:5433) is used.

What it does
------------
1. Connects to Postgres and runs a 90-day simulation (500 customers, 30-day
   CLV validation window) with sensible defaults.
2. Prints a phase-level P&L comparison (baseline vs experiment).
3. Prints a CLV calibration summary (predicted vs realised revenue).
4. Lists the 5 earliest-churning customers.
5. Tells you exactly which API calls and notebook section to explore next.

You can rerun with --seed <N> to get a different cohort.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env from repo root before importing app modules
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv

    _env = Path(__file__).resolve().parent.parent / ".env"
    if _env.exists():
        load_dotenv(_env)
        print(f"Loaded {_env}")
except ImportError:
    pass  # python-dotenv is optional; DATABASE_URL must be set in environment

# ---------------------------------------------------------------------------
# Imports (app must be importable — run with: pip install -e ".[dev]")
# ---------------------------------------------------------------------------
try:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.models.customer_lifetime import CustomerLifetimeRow
    from app.models.customer import CustomerRow
    from app.models.daily_aggregate import DailyAggregateRow
    from app.schemas.run_config import RunConfig
    from app.services.simulation.engine import create_run_record, execute_simulation
except ImportError as exc:
    sys.exit(
        f"Import error: {exc}\n"
        "Make sure you have run: pip install -e \".[dev]\"\n"
        "and that DATABASE_URL points at a live Postgres with migrations applied."
    )

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Quick-start simulation + analysis")
parser.add_argument("--seed", type=int, default=2026, help="RNG seed (default 2026)")
parser.add_argument(
    "--customers", type=int, default=500, help="Cohort size (default 500)"
)
parser.add_argument(
    "--horizon", type=int, default=90, help="Simulation horizon in days (default 90)"
)
parser.add_argument(
    "--clv-validation-days",
    type=int,
    default=30,
    dest="clv_validation_days",
    help="Extra days for CLV holdout validation (default 30)",
)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://pricing:pricing@localhost:5433/pricing_simulator",
)
if DB_URL.startswith("postgresql://") and "+psycopg" not in DB_URL:
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DB_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Build config
# ---------------------------------------------------------------------------
cfg = RunConfig(
    seed=args.seed,
    horizon_days=args.horizon,
    baseline_end_day=30,
    experiment_start_day=31,
    customer_count=args.customers,
    control_delivery_fee=2.99,
    variant_delivery_fee=1.99,
    variant_extra_discount=1.00,
    variable_cost_rate=0.35,
    churn_base_rate=0.003,
    clv_projected_days=args.clv_validation_days,
    discount_rate_annual=0.10,
    clv_validation_days=args.clv_validation_days,
)

_SEP = "─" * 60

# ---------------------------------------------------------------------------
# Run the simulation
# ---------------------------------------------------------------------------
print(f"\n{_SEP}")
print(f"  Pricing Simulator — Quick Analysis")
print(f"  seed={cfg.seed}  customers={cfg.customer_count}  horizon={cfg.horizon_days}d")
print(f"  CLV validation window: {cfg.clv_validation_days} days")
print(_SEP)

db = Session()
run_id = create_run_record(db, cfg)
print(f"\nCreated run  {run_id}")
print("Running simulation…", flush=True)
execute_simulation(db, run_id, cfg)
print(f"Done.\n")

# ---------------------------------------------------------------------------
# §1  Phase-level P&L
# ---------------------------------------------------------------------------
print(_SEP)
print("  Phase P&L — experiment vs baseline (all zones combined)")
print(_SEP)

phase_rows = db.scalars(
    select(DailyAggregateRow)
    .where(DailyAggregateRow.run_id == run_id)
    .where(DailyAggregateRow.location_zone == "__all__")
    .where(DailyAggregateRow.treatment.is_(None))
).all()

from collections import defaultdict

phase_totals: dict[str, dict[str, float]] = defaultdict(
    lambda: {"days": 0, "orders": 0, "gross": 0.0, "net": 0.0, "margin": 0.0, "inc_orders": 0}
)
for row in phase_rows:
    m = row.metrics
    p = phase_totals[row.phase]
    p["days"] += 1
    p["orders"] += m.get("orders", 0)
    p["gross"] += m.get("gross_revenue", 0.0)
    p["net"] += m.get("net_revenue", 0.0)
    p["margin"] += m.get("contribution_margin", 0.0)
    p["inc_orders"] += m.get("incremental_orders", 0)

for phase, t in sorted(phase_totals.items()):
    days = t["days"]
    print(
        f"  {phase:<12} "
        f"days={days:>3}  orders={t['orders']:>5}  "
        f"net_rev=${t['net']:>8.2f}  margin=${t['margin']:>8.2f}"
        + (f"  inc_orders={t['inc_orders']}" if phase == "experiment" else "")
    )

# ---------------------------------------------------------------------------
# §2  Experiment arm breakdown
# ---------------------------------------------------------------------------
arm_rows = db.scalars(
    select(DailyAggregateRow)
    .where(DailyAggregateRow.run_id == run_id)
    .where(DailyAggregateRow.phase == "experiment")
    .where(DailyAggregateRow.location_zone == "__all__")
    .where(DailyAggregateRow.treatment.isnot(None))
).all()

arm_totals: dict[str, dict[str, float]] = defaultdict(
    lambda: {"orders": 0, "net": 0.0, "margin": 0.0, "inc_orders": 0, "conv_sum": 0.0, "n": 0}
)
for row in arm_rows:
    m = row.metrics
    t = arm_totals[row.treatment or "unknown"]
    t["orders"] += m.get("orders", 0)
    t["net"] += m.get("net_revenue", 0.0)
    t["margin"] += m.get("contribution_margin", 0.0)
    t["inc_orders"] += m.get("incremental_orders", 0)
    t["conv_sum"] += m.get("conversion_rate", 0.0)
    t["n"] += 1

if arm_totals:
    print(f"\n{'':4}{'Arm':<10} {'Orders':>7} {'Net rev':>10} {'Margin':>9} {'Inc orders':>11} {'Avg conv%':>10}")
    for arm, t in sorted(arm_totals.items()):
        avg_conv = (t["conv_sum"] / t["n"] * 100) if t["n"] else 0.0
        print(
            f"    {arm:<10} {t['orders']:>7}  ${t['net']:>9.2f}  ${t['margin']:>8.2f}  "
            f"{t['inc_orders']:>10}   {avg_conv:>8.1f}%"
        )
else:
    print("  (no experiment phase data — horizon_days < experiment_start_day)")

# ---------------------------------------------------------------------------
# §3  CLV calibration
# ---------------------------------------------------------------------------
print(f"\n{_SEP}")
print(f"  CLV Model — predicted vs {cfg.clv_validation_days}-day holdout")
print(_SEP)

ltv_rows = db.scalars(
    select(CustomerLifetimeRow).where(CustomerLifetimeRow.run_id == run_id)
).all()

import math

predicted = [r.predicted_clv for r in ltv_rows]
actual = [r.actual_clv_validation_revenue or 0.0 for r in ltv_rows]
n = len(predicted)
churned = sum(1 for r in ltv_rows if r.churned_day is not None)

mean_pred = sum(predicted) / n
mean_actual = sum(actual) / n
rmse = math.sqrt(sum((p - a) ** 2 for p, a in zip(predicted, actual)) / n)
mae = sum(abs(p - a) for p, a in zip(predicted, actual)) / n
# Relative bias only over customers who had nonzero actual revenue (avoids division noise)
nonzero_pairs = [(p, a) for p, a in zip(predicted, actual) if a > 0.01]
if nonzero_pairs:
    mean_rel_bias = sum((p - a) / a for p, a in nonzero_pairs) / len(nonzero_pairs)
    bias_denominator_note = f"(over {len(nonzero_pairs)} customers with actual > $0)"
else:
    mean_rel_bias = 0.0
    bias_denominator_note = "(no customers with actual > $0)"

print(f"  Customers     : {n}")
print(f"  Churned       : {churned}  ({churned / n * 100:.1f}%)")
print(f"  Mean predicted: ${mean_pred:.2f}")
print(f"  Mean actual   : ${mean_actual:.2f}")
print(f"  RMSE          : ${rmse:.2f}")
print(f"  MAE           : ${mae:.2f}")
bias_dir = "over-predicts" if mean_rel_bias > 0 else "under-predicts"
print(f"  Mean rel bias : {mean_rel_bias:+.2f}  (model {bias_dir}) {bias_denominator_note}")

# ---------------------------------------------------------------------------
# §4  Earliest churners
# ---------------------------------------------------------------------------
churners = sorted(
    [r for r in ltv_rows if r.churned_day is not None],
    key=lambda r: r.churned_day or 9999,
)[:5]

if churners:
    print(f"\n{_SEP}")
    print("  5 earliest churners")
    print(_SEP)
    cust_ids = [r.customer_id for r in churners]
    cust_rows = {
        c.id: c
        for c in db.scalars(
            select(CustomerRow).where(CustomerRow.id.in_(cust_ids))
        ).all()
    }
    print(f"  {'Customer':>10} {'Churn day':>10} {'Orders':>7} {'Revenue':>9} {'Zone':>6} {'Propensity':>11}")
    for r in churners:
        c = cust_rows.get(r.customer_id)
        zone = c.location_zone if c else "?"
        prop = f"{c.buy_propensity:.3f}" if c else "?"
        print(
            f"  {r.customer_id:>10} {r.churned_day or 0:>10} {r.total_orders:>7} "
            f"${r.total_net_revenue:>8.2f} {zone:>6} {prop:>11}"
        )

db.close()

# ---------------------------------------------------------------------------
# §5  What to do next
# ---------------------------------------------------------------------------
run_id_str = str(run_id)
print(f"\n{_SEP}")
print("  What to do next")
print(_SEP)
print(f"""
  Run ID: {run_id_str}

  API — inspect this run:
    curl http://127.0.0.1:8000/api/runs/{run_id_str}
    curl "http://127.0.0.1:8000/api/runs/{run_id_str}/daily?phase=experiment"
    curl http://127.0.0.1:8000/api/runs/{run_id_str}/customer-ltv | python3 -m json.tool | head -60

  Notebooks (from repo root, venv active):
    jupyter lab notebooks/simulation_walkthrough.ipynb
      → §6–11  full run analysis, A/B comparison, customer journeys
      → §12    CLV validation charts (scatter, error dist, calibration)

  UI:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    cd frontend && npm run dev
    # open http://localhost:5173

  Re-run with a different seed:
    python scripts/quick_analysis.py --seed 42 --customers 1000
""")
print(_SEP)
