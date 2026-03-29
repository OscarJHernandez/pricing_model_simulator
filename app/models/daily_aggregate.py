import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.schemas.day_metrics import DayMetrics


class DailyAggregateRow(Base):
    __tablename__ = "daily_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "day",
            "phase",
            "treatment",
            "location_zone",
            name="uq_agg_run_day_phase_treat_zone",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    treatment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    location_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metrics: Mapped[DayMetrics] = mapped_column(JSONB, nullable=False)

    run = relationship("SimulationRunRow", back_populates="daily_aggregates")
