from __future__ import annotations

import numpy as np

from app.domain.customer import Customer


def assign_treatments(customers: list[Customer], rng: np.random.Generator) -> None:
    for c in customers:
        c.assigned_treatment = "variant" if rng.random() < 0.5 else "control"
