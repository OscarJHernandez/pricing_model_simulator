"""Integration: experiment-phase rollups from persisted daily aggregates."""

from __future__ import annotations

import os

import pytest

from app.db.session import SessionLocal
from app.models.simulation_run import SimulationRunRow
from app.schemas.run_config import RunConfig
from app.services.simulation.engine import create_run_record, execute_simulation
from app.services.stats.inference import build_experiment_inference, load_experiment_arm_rollups

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL required for rollup loader integration test",
)


def test_load_experiment_arm_rollups_after_simulation() -> None:
    cfg = RunConfig.model_validate(
        {
            "seed": 991_001,
            "horizon_days": 20,
            "baseline_end_day": 6,
            "experiment_start_day": 9,
            "customer_count": 24,
        }
    )
    db = SessionLocal()
    try:
        run_id = create_run_record(db, cfg)
        run = db.get(SimulationRunRow, run_id)
        assert run is not None
        run.status = "running"
        db.commit()

        execute_simulation(db, run_id, cfg)

        ctrl, var = load_experiment_arm_rollups(db, run_id)
        assert ctrl.customer_days + var.customer_days > 0

        out = build_experiment_inference(
            run_id=str(run_id),
            control=ctrl,
            variant=var,
            prior_alpha=1.0,
            prior_beta=1.0,
        )
        assert out.control.customer_days == ctrl.customer_days
        assert out.variant.customer_days == var.customer_days
        assert out.bayesian.prior_alpha == 1.0
    finally:
        db.close()
