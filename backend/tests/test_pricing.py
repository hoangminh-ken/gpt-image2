from decimal import Decimal

from app.core.pricing import compute_cost, resolve_pricing


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


def test_default_model_gpt_image_2():
    # 1M input × $8 + 1M output × $30 = $38
    assert compute_cost(1_000_000, 1_000_000, model="gpt-image-2") == Decimal("38.000000")


def test_resolve_known_models():
    assert resolve_pricing("gpt-image-2") == (Decimal("8.00"), Decimal("30.00"))
    assert resolve_pricing("gpt-image-1.5") == (Decimal("8.00"), Decimal("32.00"))
    assert resolve_pricing("gpt-image-1-mini") == (Decimal("2.50"), Decimal("8.00"))


def test_resolve_snapshot_by_prefix():
    # snapshot ID like 'gpt-image-2-2026-04-21' → falls back to 'gpt-image-2' alias
    assert resolve_pricing("gpt-image-2-2026-04-21") == (Decimal("8.00"), Decimal("30.00"))


def test_resolve_unknown_falls_back_to_default():
    assert resolve_pricing("totally-made-up-model") == (Decimal("8.00"), Decimal("30.00"))


def test_smoke_replay_phase1():
    # Phase 1 smoke recorded: 2461 in, 1756 out → $0.072368 with gpt-image-2 pricing
    assert compute_cost(2461, 1756, model="gpt-image-2") == Decimal("0.072368")


def test_mini_pricing_distinct():
    # Mini is 5× cheaper output than std → 1k+1k tokens diff
    std = compute_cost(10_000, 10_000, model="gpt-image-2")        # $0.08+$0.30 = $0.38
    mini = compute_cost(10_000, 10_000, model="gpt-image-1-mini")  # $0.025+$0.08 = $0.105
    assert std == Decimal("0.380000")
    assert mini == Decimal("0.105000")
    assert mini < std
