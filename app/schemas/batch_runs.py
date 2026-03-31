"""Request body for creating multiple runs with different seeds."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.run_config import RunConfig


class BatchRunsBody(BaseModel):
    """Same simulation configuration executed once per seed (spec section 9)."""

    seeds: list[int] = Field(..., min_length=1, max_length=50)
    run: RunConfig
