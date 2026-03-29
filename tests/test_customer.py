import numpy as np

from app.domain.customer import Customer, PurchaseContext


def test_over_budget_zero_probability():
    c = Customer(
        customer_id=1,
        customer_index=0,
        budget=10.0,
        buy_propensity=0.9,
        price_threshold=8.0,
        repeat_boost=0.3,
        basket_mean=12.0,
        location_zone="A",
    )
    ctx = PurchaseContext(1.0, 1.0, True)
    assert c.compute_purchase_probability(50.0, 1, ctx) == 0.0


def test_returning_easier_than_new():
    rng = np.random.default_rng(0)
    ctx = PurchaseContext(1.0, 1.0, True)
    new = Customer(
        1, 0, 50.0, 0.25, 30.0, 0.4, 18.0, "A"
    )
    ret = Customer(
        2,
        1,
        50.0,
        0.25,
        30.0,
        0.4,
        18.0,
        "A",
        has_purchased_before=True,
        purchase_count=2,
    )
    p_new = new.compute_purchase_probability(28.0, 3, ctx)
    p_ret = ret.compute_purchase_probability(28.0, 3, ctx)
    assert p_ret >= p_new
