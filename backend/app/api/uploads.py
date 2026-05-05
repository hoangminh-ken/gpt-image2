"""Upload reference images for Mode A drag-drop. Files saved to UPLOAD_DIR."""
from __future__ import annotations

import contextlib
import time
import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.config import settings
from app.utils.slug import store_path

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}
MAX_BYTES = 100 * 1024 * 1024  # 100MB — Pillow auto-resizes to MAX_REF_DIMENSION before API call
MAX_FILES = 16
RETENTION_DAYS = 7


def _save_one(file: UploadFile) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(415, f"Unsupported type: {suffix or '(none)'}")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, f"Unsupported content-type: {file.content_type}")

    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_BYTES} bytes")

    today = date.today().isoformat()
    folder = settings.upload_path / today
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{suffix}"
    target = folder / name
    target.write_bytes(data)

    return {
        "name": file.filename,
        "path": store_path(target, settings.project_root),
        "abs_path": str(target),
        "size": len(data),
    }


@router.post("/refs")
async def upload_refs(files: list[UploadFile]) -> dict:
    if not files:
        raise HTTPException(400, "No files provided")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Too many files (max {MAX_FILES})")
    saved = [_save_one(f) for f in files]
    return {"files": saved}


def cleanup_old_uploads() -> int:
    """Delete files older than RETENTION_DAYS. Best-effort, called at startup."""
    cutoff = time.time() - RETENTION_DAYS * 86400
    removed = 0
    root = settings.upload_path
    if not root.exists():
        return 0
    for child in root.rglob("*"):
        if child.is_file():
            try:
                if child.stat().st_mtime < cutoff:
                    child.unlink()
                    removed += 1
            except OSError:
                continue
    # remove empty date-named dirs
    for d in root.iterdir():
        if not d.is_dir():
            continue
        try:
            date.fromisoformat(d.name)
        except ValueError:
            continue
        if not any(d.iterdir()):
            with contextlib.suppress(OSError):
                d.rmdir()
    return removed
