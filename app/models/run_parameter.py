import uuid
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RunParameterRow(Base):
    """Full scenario config as JSON plus a few indexed scalars for listing."""

    __tablename__ = "run_parameters"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    run = relationship("SimulationRunRow", back_populates="parameters")
