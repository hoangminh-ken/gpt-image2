from decimal import Decimal

from app.core.pricing import compute_cost


def test_zero_tokens():
    assert compute_cost(0, 0) == Decimal("0.000000")


def test_input_only():
    # 1M input tokens × $8 = $8.000000
    assert compute_cost(1_000_000, 0) == Decimal("8.000000")


def test_output_only():
    assert compute_cost(0, 1_000_000) == Decimal("30.000000")


def test_mixed_realistic():
    # ~10k input + ~4k output → small usd
    cost = compute_cost(10_000, 4_000)
    # 10k×8/1M + 4k×30/1M = 0.08 + 0.12 = 0.20
    assert cost == Decimal("0.200000")


def test_override():
    cost = compute_cost(
        1_000_000, 0,
        input_price_per_m=Decimal("10.00"),
        output_price_per_m=Decimal("40.00"),
    )
    assert cost == Decimal("10.000000")
