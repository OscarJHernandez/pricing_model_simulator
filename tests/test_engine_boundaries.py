"""Targeted simulation engine tests: cohort size, washout phase, CLV validation."""

from __future__ import annotations

import os

import numpy as np
import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.customer_lifetime import CustomerLifetimeRow
from app.models.daily_aggregate import DailyAggregateRow
from app.models.simulation_run import SimulationRunRow
from app.schemas.run_config import RunConfig
from app.services.simulation.engine import (
    create_run_record,
    execute_simulation,
    generate_customers,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL required for engine boundary tests",
)


def test_generate_customers_respects_config_count() -> None:
    cfg = RunConfig.model_validate(
        {
            "seed": 1,
            "customer_count": 1,
            "baseline_end_day": 10,
            "experiment_start_day": 20,
            "horizon_days": 25,
        }
    )
    rng = np.random.default_rng(0)
    one = generate_customers(cfg, rng)
    assert len(one) == 1

    cfg_three = cfg.model_copy(update={"customer_count": 3})
    rng2 = np.random.default_rng(0)
    three = generate_customers(cfg_three, rng2)
    assert len(three) == 3


def test_execute_simulation_persists_washout_when_phase_gap() -> None:
    cfg = RunConfig.model_validate(
        {
            "seed": 77,
            "horizon_days": 8,
            "baseline_end_day": 2,
            "experiment_start_day": 6,
            "customer_count": 4,
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

        wash = db.scalars(
            select(DailyAggregateRow).where(
                DailyAggregateRow.run_id == run_id,
                DailyAggregateRow.phase == "washout",
            )
        ).all()
        assert len(wash) > 0
    finally:
        db.close()


def test_execute_simulation_clv_validation_sets_actual_revenue_field() -> None:
    cfg = RunConfig.model_validate(
        {
            "seed": 88,
            "horizon_days": 5,
            "baseline_end_day": 2,
            "experiment_start_day": 4,
            "customer_count": 4,
            "clv_validation_days": 3,
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

        rows = db.scalars(
            select(CustomerLifetimeRow).where(CustomerLifetimeRow.run_id == run_id)
        ).all()
        assert len(rows) == cfg.customer_count
        for row in rows:
            assert row.actual_clv_validation_revenue is not None
    finally:
        db.close()
