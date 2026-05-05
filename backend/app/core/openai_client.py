"""Thin wrapper around openai SDK for gpt-image-2 edit calls.

Reference: https://developers.openai.com/api/docs/models/gpt-image-2
- Endpoint: client.images.edit (POST /v1/images/edits)
- Response default: b64_json (returned in resp.data[0].b64_json)
- Usage: resp.usage.{input_tokens, output_tokens, total_tokens}

Provides both sync (`edit_image`) and async (`edit_image_async`) variants.
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI, OpenAI
from PIL import Image

from app.config import settings

DEFAULT_SIZE = "1024x1024"   # also valid: 1024x1536, 1536x1024, auto
DEFAULT_QUALITY = "medium"   # low | medium | high | auto
DEFAULT_OUTPUT_FORMAT = "png"


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


def _async_client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured in .env")
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _prepare_image_arg(ref_paths: list[str]):
    if not ref_paths:
        raise ValueError("At least one reference image path is required")
    files = []
    for p in ref_paths:
        path = Path(p)
        if not path.is_file():
            raise FileNotFoundError(f"Reference image not found: {p}")
        png_bytes = _resize_if_needed(path, settings.max_ref_dimension)
        files.append((path.name, png_bytes, "image/png"))
    return files[0] if len(files) == 1 else files


def _parse_response(resp) -> EditResult:
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


def edit_image(
    prompt: str,
    ref_paths: list[str],
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
) -> EditResult:
    """Call gpt-image-2 edit with one or more reference images.

    Returns generated PNG bytes plus token usage from response.usage.
    """
    image_arg = _prepare_image_arg(ref_paths)
    resp = _client().images.edit(
        model=settings.openai_image_model,
        image=image_arg,
        prompt=prompt,
        size=size,
        quality=quality,
        output_format=DEFAULT_OUTPUT_FORMAT,
    )
    return _parse_response(resp)


async def edit_image_async(
    prompt: str,
    ref_paths: list[str],
    size: str = DEFAULT_SIZE,
    quality: str = DEFAULT_QUALITY,
) -> EditResult:
    """Async variant. Image prep is sync (CPU/IO short), API call is awaited."""
    image_arg = _prepare_image_arg(ref_paths)
    client = _async_client()
    resp = await client.images.edit(
        model=settings.openai_image_model,
        image=image_arg,
        prompt=prompt,
        size=size,
        quality=quality,
        output_format=DEFAULT_OUTPUT_FORMAT,
    )
    return _parse_response(resp)
