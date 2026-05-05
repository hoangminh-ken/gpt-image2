"""Serve generated PNGs and uploaded refs from disk.

Two roots: strict (OUTPUT_DIR + UPLOAD_DIR) and ref-image (any path with image extension).
Localhost-only single-user — broader access acceptable for ref previews.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(prefix="/api/preview", tags=["preview"])

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _resolve_safe(rel: str) -> Path:
    """Resolve a path. Strict for outputs/uploads; permissive for image refs (localhost only).

    1. Reject `..` segments (defense in depth)
    2. If under OUTPUT_DIR / UPLOAD_DIR / project_root → allow any file
    3. Else if absolute path with image extension and exists → allow (ref preview)
    4. Otherwise 403
    """
    if not rel or ".." in rel.split("/"):
        raise HTTPException(400, "Invalid path")

    candidate = Path(rel)
    if not candidate.is_absolute():
        candidate = settings.project_root / candidate
    candidate = candidate.resolve()

    if not candidate.is_file():
        raise HTTPException(404, "File not found")

    allowed_roots = [
        settings.output_path.resolve(),
        settings.upload_path.resolve(),
        settings.project_root.resolve(),
    ]
    in_root = any(str(candidate).startswith(str(root)) for root in allowed_roots)
    is_image = candidate.suffix.lower() in IMAGE_EXTS

    if not in_root and not is_image:
        raise HTTPException(403, "Path not allowed")

    return candidate


@router.get("/{path:path}")
def serve(path: str) -> FileResponse:
    file = _resolve_safe(path)
    return FileResponse(file)
