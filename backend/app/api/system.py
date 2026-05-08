"""System endpoints: open output folder in OS file manager."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])


class OpenFolderRequest(BaseModel):
    path: str
    select_file: bool = False  # if True, opens parent and highlights the file


def _validate_path(path_str: str) -> Path:
    """Reject `..` segments, ensure path exists. Localhost-only — user already
    has full disk access; this endpoint just opens whatever they ask for, akin
    to running `explorer.exe <path>` themselves. Mode C output dirs live wherever
    user chose, so we can't restrict to OUTPUT_DIR/UPLOAD_DIR anymore."""
    if ".." in path_str.replace("\\", "/").split("/"):
        raise HTTPException(400, "Invalid path")
    p = Path(path_str).expanduser()
    p = (settings.project_root / p).resolve() if not p.is_absolute() else p.resolve()
    if not p.exists():
        raise HTTPException(404, f"Path not found: {p}")
    return p


def _open(path: Path, select_file: bool) -> None:
    if sys.platform == "win32":
        if select_file and path.is_file():
            subprocess.Popen(["explorer.exe", "/select,", str(path)])
        else:
            target = path if path.is_dir() else path.parent
            os.startfile(str(target))  # type: ignore[attr-defined]  # noqa: S606
    elif sys.platform == "darwin":
        if select_file and path.is_file():
            subprocess.Popen(["open", "-R", str(path)])
        else:
            target = path if path.is_dir() else path.parent
            subprocess.Popen(["open", str(target)])
    else:
        target = path if path.is_dir() else path.parent
        subprocess.Popen(["xdg-open", str(target)])


@router.post("/open-folder")
def open_folder(payload: OpenFolderRequest) -> dict:
    p = _validate_path(payload.path)
    try:
        _open(p, payload.select_file)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Failed to open: {exc}") from exc
    return {"ok": True, "opened": str(p)}
