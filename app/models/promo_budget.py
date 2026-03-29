import uuid

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PromoBudgetTrackingRow(Base):
    __tablename__ = "promo_budget_tracking"
    __table_args__ = (UniqueConstraint("run_id", "day", name="uq_promo_budget_run_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    discount_spend_day: Mapped[float] = mapped_column(Float, nullable=False)
    cumulative_discount_spend: Mapped[float] = mapped_column(Float, nullable=False)
    remaining_budget: Mapped[float | None] = mapped_column(Float, nullable=True)

    run = relationship("SimulationRunRow", back_populates="promo_budget_rows")
