def zone_multiplier(zone: str, modifiers: dict[str, float] | None = None) -> float:
    defaults = {"A": 1.0, "B": 1.08, "C": 0.92}
    m = {**defaults, **(modifiers or {})}
    return float(m.get(zone, 1.0))
