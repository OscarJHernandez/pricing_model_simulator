"""Randomized experiment arm assignment for the customer cohort."""

from __future__ import annotations

import numpy as np

from app.domain.customer import Customer


def assign_treatments(
    customers: list[Customer], rng: np.random.Generator, split: float = 0.5
) -> None:
    """Assign each customer independently to variant with probability ``split``, else control."""
    for c in customers:
        c.assigned_treatment = "variant" if rng.random() < split else "control"
