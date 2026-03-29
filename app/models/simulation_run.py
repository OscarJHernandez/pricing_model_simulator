import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SimulationRunRow(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    baseline_end_day: Mapped[int] = mapped_column(Integer, nullable=False)
    experiment_start_day: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    parameters = relationship("RunParameterRow", back_populates="run", uselist=False)
    customers = relationship("CustomerRow", back_populates="run")
    assignments = relationship("ExperimentAssignmentRow", back_populates="run")
    daily_outcomes = relationship("DailyCustomerOutcomeRow", back_populates="run")
    daily_aggregates = relationship("DailyAggregateRow", back_populates="run")
    promo_budget_rows = relationship("PromoBudgetTrackingRow", back_populates="run")
