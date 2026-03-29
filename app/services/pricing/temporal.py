"""Simple calendar multipliers (weekend vs weekday plus mild seasonality)."""


def temporal_multiplier(
    day: int,
    *,
    weekend_factor: float = 1.12,
    weekday_factor: float = 1.0,
    seasonal_amplitude: float = 0.05,
) -> float:
    """Simple weekday vs weekend + mild sine seasonality by day index."""
    # day 1 = Monday for illustration: (day-1) % 7
    dow = (day - 1) % 7
    is_weekend = dow >= 5
    base = weekend_factor if is_weekend else weekday_factor
    season = 1.0 + seasonal_amplitude * __import__("math").sin(day / 14.0)
    return float(base * season)


def is_weekend(day: int) -> bool:
    """True when simulated day index maps to Saturday or Sunday (day 1 = Monday)."""
    dow = (day - 1) % 7
    return dow >= 5
