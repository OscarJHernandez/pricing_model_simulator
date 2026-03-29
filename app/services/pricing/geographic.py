"""Zone-level demand multipliers with optional overrides from run configuration."""


def zone_multiplier(zone: str, modifiers: dict[str, float] | None = None) -> float:
    """Return demand multiplier for ``zone``; unknown zones default to 1.0."""
    defaults = {"A": 1.0, "B": 1.08, "C": 0.92}
    m = {**defaults, **(modifiers or {})}
    return float(m.get(zone, 1.0))
