"""Mode A parser: template prompt + list of refs → list of items."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ItemSpec:
    row_idx: int
    prompt: str
    refs: list[str]
    output_name: str | None = None


def build_items(template_prompt: str, ref_paths: list[str]) -> list[ItemSpec]:
    """One item per reference image, all sharing the same template prompt."""
    if not template_prompt or not template_prompt.strip():
        raise ValueError("template_prompt is required")
    if not ref_paths:
        raise ValueError("ref_paths must contain at least one path")
    return [
        ItemSpec(row_idx=i, prompt=template_prompt, refs=[p])
        for i, p in enumerate(ref_paths)
    ]
