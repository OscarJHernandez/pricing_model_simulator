"""Incrementality: single uniform draw vs control and variant purchase thresholds."""


def incremental_variant_order(purchased: bool, u: float, p_control: float) -> bool:
    """True if the customer bought but the same uniform draw would not buy at control.

    The engine uses a single uniform ``u`` compared to variant vs control purchase
    probabilities; this helper documents that coupling for standalone tests.
    """
    if not purchased:
        return False
    return u >= p_control
