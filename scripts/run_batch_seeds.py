#!/usr/bin/env python3
"""Run the same RunConfig for multiple seeds synchronously (spec section 9). Requires PostgreSQL.

Example:
  python scripts/run_batch_seeds.py --seeds 1,2,3 --customers 200 --horizon 60
"""

from __future__ import annotations

import argparse
import sys

from app.db.session import SessionLocal
from app.models.simulation_run import SimulationRunRow
from app.schemas.run_config import RunConfig
from app.services.simulation.engine import create_run_record, execute_simulation


def main() -> None:
    p = argparse.ArgumentParser(description="Batch simulation runs by seed (synchronous)")
    p.add_argument("--seeds", required=True, help="Comma-separated integers, e.g. 1,2,3,4")
    p.add_argument("--customers", type=int, default=None)
    p.add_argument("--horizon", type=int, default=None)
    args = p.parse_args()
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    if not seeds:
        print("No seeds provided", file=sys.stderr)
        sys.exit(1)

    base = RunConfig.model_validate({"seed": seeds[0]})
    data = base.model_dump()
    if args.customers is not None:
        data["customer_count"] = args.customers
    if args.horizon is not None:
        data["horizon_days"] = args.horizon

    db = SessionLocal()
    try:
        for seed in seeds:
            cfg = RunConfig.model_validate({**data, "seed": seed})
            rid = create_run_record(db, cfg)
            run = db.get(SimulationRunRow, rid)
            if run:
                run.status = "running"
                db.commit()
            execute_simulation(db, rid, cfg)
            print(f"seed={seed} run_id={rid} status=completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
