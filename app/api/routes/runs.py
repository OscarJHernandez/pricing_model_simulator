from __future__ import annotations

import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.customer import CustomerRow
from app.models.daily_aggregate import DailyAggregateRow
from app.models.daily_customer_outcome import DailyCustomerOutcomeRow
from app.models.experiment_assignment import ExperimentAssignmentRow
from app.models.simulation_run import SimulationRunRow
from app.schemas.run_config import RunConfig
from app.services.simulation.engine import create_run_record, execute_simulation

router = APIRouter()


def _run_simulation_job(run_id: uuid.UUID, payload: dict[str, Any]) -> None:
    config = RunConfig.model_validate(payload)
    db = SessionLocal()
    try:
        run = db.get(SimulationRunRow, run_id)
        if not run:
            return
        run.status = "running"
        db.commit()
        execute_simulation(db, run_id, config)
    except Exception:
        db.rollback()
        run = db.get(SimulationRunRow, run_id)
        if run:
            run.status = "failed"
            run.error_message = traceback.format_exc()[:8000]
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("", status_code=202)
def create_run(
    body: RunConfig,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run_id = create_run_record(db, body)
    background_tasks.add_task(_run_simulation_job, run_id, body.model_dump())
    return {"id": str(run_id), "status": "pending"}


@router.get("")
def list_runs(
    db: Session = Depends(get_db),
    limit: int = 50,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(SimulationRunRow).order_by(SimulationRunRow.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "status": r.status,
            "seed": r.seed,
            "horizon_days": r.horizon_days,
            "customer_count": r.customer_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]


@router.get("/{run_id}")
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    r = db.get(SimulationRunRow, run_id)
    if not r:
        raise HTTPException(404, "Run not found")
    return {
        "id": str(r.id),
        "status": r.status,
        "seed": r.seed,
        "horizon_days": r.horizon_days,
        "baseline_end_day": r.baseline_end_day,
        "experiment_start_day": r.experiment_start_day,
        "customer_count": r.customer_count,
        "error_message": r.error_message,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "parameters": r.parameters.config if r.parameters else {},
    }


@router.get("/{run_id}/daily")
def get_daily(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    phase: str | None = None,
) -> list[dict[str, Any]]:
    q = select(DailyAggregateRow).where(DailyAggregateRow.run_id == run_id)
    if phase:
        q = q.where(DailyAggregateRow.phase == phase)
    q = q.order_by(DailyAggregateRow.day, DailyAggregateRow.phase, DailyAggregateRow.treatment)
    rows = db.scalars(q).all()
    return [
        {
            "day": row.day,
            "phase": row.phase,
            "treatment": row.treatment,
            "location_zone": row.location_zone,
            "metrics": row.metrics,
        }
        for row in rows
    ]


@router.get("/{run_id}/customers")
def get_customers(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    limit: int = 500,
    offset: int = 0,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(CustomerRow)
        .where(CustomerRow.run_id == run_id)
        .order_by(CustomerRow.customer_index)
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": c.id,
            "customer_index": c.customer_index,
            "budget": c.budget,
            "buy_propensity": c.buy_propensity,
            "price_threshold": c.price_threshold,
            "basket_mean": c.basket_mean,
            "location_zone": c.location_zone,
        }
        for c in rows
    ]


@router.get("/{run_id}/treatments")
def get_treatments(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(ExperimentAssignmentRow).where(ExperimentAssignmentRow.run_id == run_id)
    ).all()
    return [
        {"customer_id": row.customer_id, "treatment": row.treatment} for row in rows
    ]


@router.get("/{run_id}/outcomes/sample")
def sample_outcomes(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    limit: int = 200,
) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(DailyCustomerOutcomeRow)
        .where(DailyCustomerOutcomeRow.run_id == run_id)
        .order_by(DailyCustomerOutcomeRow.day, DailyCustomerOutcomeRow.id)
        .limit(limit)
    ).all()
    return [
        {
            "day": o.day,
            "customer_id": o.customer_id,
            "phase": o.phase,
            "treatment": o.treatment,
            "purchased": o.purchased,
            "incremental_order": o.incremental_order,
            "net_revenue": o.net_revenue,
        }
        for o in rows
    ]
