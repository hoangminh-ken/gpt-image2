"""Token → USD cost calculation, per-model pricing table.

Source: https://developers.openai.com/api/docs/pricing (verified May 2026).
- gpt-image-2:       Input $8.00/M, Output $30.00/M (cached input $2.00/M, not tracked here)
- gpt-image-1.5:     Input $8.00/M, Output $32.00/M
- gpt-image-1-mini:  Input $2.50/M, Output $8.00/M
- gpt-image-1:       Input $5.00/M, Output $40.00/M  (legacy; verify before relying)

Model snapshot suffixes (e.g. gpt-image-2-2026-04-21) resolve to the alias by prefix match.
"""
from __future__ import annotations

from decimal import Decimal

PER_M = Decimal("1000000")

# (input_per_M, output_per_M)
MODEL_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-image-2":      (Decimal("8.00"),  Decimal("30.00")),
    "gpt-image-1.5":    (Decimal("8.00"),  Decimal("32.00")),
    "gpt-image-1-mini": (Decimal("2.50"),  Decimal("8.00")),
    "gpt-image-1":      (Decimal("5.00"),  Decimal("40.00")),
}

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_INPUT_PRICE_PER_M = MODEL_PRICING[DEFAULT_MODEL][0]
DEFAULT_OUTPUT_PRICE_PER_M = MODEL_PRICING[DEFAULT_MODEL][1]

# Back-compat exports for older callers/tests
INPUT_PRICE_PER_M = DEFAULT_INPUT_PRICE_PER_M
OUTPUT_PRICE_PER_M = DEFAULT_OUTPUT_PRICE_PER_M


def resolve_pricing(model: str) -> tuple[Decimal, Decimal]:
    """Look up pricing for a model. Falls back to alias by prefix match."""
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    # snapshot like 'gpt-image-2-2026-04-21' → match longest known prefix
    candidates = sorted(
        (k for k in MODEL_PRICING if model.startswith(k)),
        key=len, reverse=True,
    )
    if candidates:
        return MODEL_PRICING[candidates[0]]
    return MODEL_PRICING[DEFAULT_MODEL]


def compute_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = DEFAULT_MODEL,
    input_price_per_m: Decimal | None = None,
    output_price_per_m: Decimal | None = None,
) -> Decimal:
    """Return USD cost. Explicit overrides win over model lookup."""
    if input_price_per_m is None or output_price_per_m is None:
        in_p, out_p = resolve_pricing(model)
        if input_price_per_m is None:
            input_price_per_m = in_p
        if output_price_per_m is None:
            output_price_per_m = out_p
    cost = (Decimal(input_tokens) * input_price_per_m + Decimal(output_tokens) * output_price_per_m) / PER_M
    return cost.quantize(Decimal("0.000001"))
