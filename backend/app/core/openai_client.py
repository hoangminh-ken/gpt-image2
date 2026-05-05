"""Thin wrapper around openai SDK for gpt-image-2 edit calls.

Phase 1: synchronous. Phase 2 will introduce AsyncOpenAI variant.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from PIL import Image

from app.config import settings

MODEL = "gpt-image-2"
DEFAULT_SIZE = "1024x1024"
DEFAULT_QUALITY = "medium"


@dataclass
class EditResult:
    image_bytes: bytes
    input_tokens: int
    output_tokens: int


def _resize_if_needed(path: Path, max_dim: int) -> bytes:
    """Open image, resize so longest side ≤ max_dim, return PNG bytes."""
    with Image.open(path) as img:
        img = img.convert("RGBA") if img.mode in ("P", "LA") else img.convert("RGB")
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured in .env")
    return OpenAI(api_key=settings.openai_api_key)


def edit_image(
    prompt: str,
    ref_paths: list[str],
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
) -> EditResult:
    """Call gpt-image-2 edit with one or more reference images.

    Returns generated PNG bytes plus token usage from response.usage.
    """
    if not ref_paths:
        raise ValueError("At least one reference image path is required")

    files = []
    try:
        for p in ref_paths:
            path = Path(p)
            if not path.is_file():
                raise FileNotFoundError(f"Reference image not found: {p}")
            png_bytes = _resize_if_needed(path, settings.max_ref_dimension)
            files.append((path.name, png_bytes, "image/png"))

        # openai SDK accepts a list of file tuples for multiple references
        image_arg = [(name, buf, mime) for name, buf, mime in files]
        if len(image_arg) == 1:
            image_arg = image_arg[0]

        resp = _client().images.edit(
            model=MODEL,
            image=image_arg,
            prompt=prompt,
            size=size,
            quality=quality,
        )
    finally:
        files.clear()

    if not resp.data:
        raise RuntimeError("OpenAI returned no image data")

    b64 = resp.data[0].b64_json
    if not b64:
        raise RuntimeError("OpenAI response missing b64_json")
    image_bytes = base64.b64decode(b64)

    usage = getattr(resp, "usage", None)
    in_tokens = getattr(usage, "input_tokens", 0) if usage else 0
    out_tokens = getattr(usage, "output_tokens", 0) if usage else 0

    return EditResult(image_bytes=image_bytes, input_tokens=in_tokens, output_tokens=out_tokens)
