"""Incrementality: single uniform draw vs control and variant purchase thresholds."""


def incremental_variant_order(purchased: bool, u: float, p_control: float) -> bool:
    """True if the customer bought under the variant offer but would not under control."""
    if not purchased:
        return False
    return u >= p_control
