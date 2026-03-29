"""Per-customer lifetime revenue summary computed at the end of each simulation run."""

from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CustomerLifetimeRow(Base):
    __tablename__ = "customer_lifetime"
    __table_args__ = (
        UniqueConstraint("run_id", "customer_id", name="uq_customer_lifetime_run_customer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Realized metrics over the main simulation horizon
    total_orders: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_net_revenue: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_contribution_margin: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    days_active: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    churned_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # CLV model output
    predicted_clv: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Holdout validation (null when clv_validation_days == 0)
    actual_clv_validation_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)

    run = relationship("SimulationRunRow", back_populates="customer_lifetimes")
    customer_row = relationship("CustomerRow", back_populates="lifetime")
