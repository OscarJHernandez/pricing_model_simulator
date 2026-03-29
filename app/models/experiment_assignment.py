import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExperimentAssignmentRow(Base):
    __tablename__ = "experiment_assignments"

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
        unique=True,
        nullable=False,
    )
    treatment: Mapped[str] = mapped_column(String(32), nullable=False)

    run = relationship("SimulationRunRow", back_populates="assignments")
    customer_row = relationship("CustomerRow", back_populates="assignment")
