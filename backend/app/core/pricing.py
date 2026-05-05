"""Token → USD cost calculation for gpt-image-2.

Pricing (per 1M tokens, May 2026):
  - Input image/text tokens:  $8
  - Output image tokens:      $30
"""
from __future__ import annotations

from decimal import Decimal

INPUT_PRICE_PER_M = Decimal("8.00")
OUTPUT_PRICE_PER_M = Decimal("30.00")
PER_M = Decimal("1000000")


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_m: Decimal | None = None,
    output_price_per_m: Decimal | None = None,
) -> Decimal:
    """Return USD cost for given token usage."""
    inp = input_price_per_m if input_price_per_m is not None else INPUT_PRICE_PER_M
    out = output_price_per_m if output_price_per_m is not None else OUTPUT_PRICE_PER_M
    cost = (Decimal(input_tokens) * inp + Decimal(output_tokens) * out) / PER_M
    return cost.quantize(Decimal("0.000001"))
