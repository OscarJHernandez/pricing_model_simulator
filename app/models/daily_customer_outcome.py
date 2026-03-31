import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DailyCustomerOutcomeRow(Base):
    __tablename__ = "daily_customer_outcomes"
    __table_args__ = (
        UniqueConstraint("run_id", "day", "customer_id", name="uq_outcome_run_day_customer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    treatment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    offered_total_price: Mapped[float] = mapped_column(Float, nullable=False)
    purchase_probability: Mapped[float] = mapped_column(Float, nullable=False)
    purchased: Mapped[bool] = mapped_column(Boolean, nullable=False)
    order_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gross_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    net_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    variable_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contribution_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    incremental_order: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    counterfactual_would_buy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purchase_count_after_event: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    days_since_last_purchase: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run = relationship("SimulationRunRow", back_populates="daily_outcomes")
    customer_row = relationship("CustomerRow", back_populates="outcomes")
