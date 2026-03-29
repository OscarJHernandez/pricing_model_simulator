import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CustomerRow(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("run_id", "customer_index", name="uq_customers_run_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    customer_index: Mapped[int] = mapped_column(Integer, nullable=False)
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    buy_propensity: Mapped[float] = mapped_column(Float, nullable=False)
    price_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    repeat_boost: Mapped[float] = mapped_column(Float, nullable=False)
    basket_mean: Mapped[float] = mapped_column(Float, nullable=False)
    location_zone: Mapped[str] = mapped_column(String(64), nullable=False)
    acquisition_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retention_sensitivity: Mapped[float | None] = mapped_column(Float, nullable=True)
    promo_sensitivity: Mapped[float | None] = mapped_column(Float, nullable=True)

    run = relationship("SimulationRunRow", back_populates="customers")
    outcomes = relationship("DailyCustomerOutcomeRow", back_populates="customer_row")
    assignment = relationship(
        "ExperimentAssignmentRow", back_populates="customer_row", uselist=False
    )
    lifetime = relationship("CustomerLifetimeRow", back_populates="customer_row", uselist=False)
