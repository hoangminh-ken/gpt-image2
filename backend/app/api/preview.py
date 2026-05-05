"""Serve generated PNGs and uploaded refs from disk, path-traversal safe."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(prefix="/api/preview", tags=["preview"])


def _resolve_safe(rel: str) -> Path:
    """Resolve `rel` against allowed roots, reject if it escapes."""
    if not rel or ".." in rel.split("/"):
        raise HTTPException(400, "Invalid path")
    candidate = (settings.project_root / rel).resolve()
    allowed = [settings.output_path.resolve(), settings.upload_path.resolve()]
    if not any(str(candidate).startswith(str(root)) for root in allowed):
        raise HTTPException(403, "Path outside allowed roots")
    if not candidate.is_file():
        raise HTTPException(404, "File not found")
    return candidate


@router.get("/{path:path}")
def serve(path: str) -> FileResponse:
    file = _resolve_safe(path)
    return FileResponse(file)
