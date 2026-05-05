"""ZIP export of all done items in a job, streamed."""
from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Job, JobItem
from app.db.session import get_db

router = APIRouter(prefix="/api/jobs", tags=["exports"])

SAFE_RE = re.compile(r"[^a-zA-Z0-9_\-.]+")


def _safe_name(s: str) -> str:
    cleaned = SAFE_RE.sub("_", s).strip("_") or "job"
    return cleaned[:80]


def _resolve_output(rel: str) -> Path | None:
    p = settings.project_root / rel
    if p.is_file():
        return p
    abs_p = Path(rel)
    if abs_p.is_absolute() and abs_p.is_file():
        return abs_p
    return None


@router.get("/{job_id}/export.zip")
def export_zip(job_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    items = (
        db.query(JobItem)
        .filter(JobItem.job_id == job_id, JobItem.status == "done")
        .order_by(JobItem.row_idx)
        .all()
    )
    if not items:
        raise HTTPException(404, "No completed items to export")

    manifest = {
        "job_id": job.id,
        "job_name": job.name,
        "mode": job.mode,
        "items": [
            {
                "row_idx": it.row_idx,
                "prompt": it.prompt,
                "refs": it.refs_json,
                "output_name": it.output_name,
                "output_path": it.output_path,
                "input_tokens": it.input_tokens,
                "output_tokens": it.output_tokens,
                "cost_usd": float(it.cost_usd or 0),
            }
            for it in items
        ],
        "total_cost_usd": sum(float(it.cost_usd or 0) for it in items),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        for it in items:
            if not it.output_path:
                continue
            p = _resolve_output(it.output_path)
            if p is None:
                continue
            arcname = Path(it.output_path).name
            zf.write(p, arcname=arcname)
    buf.seek(0)

    fname = f"{_safe_name(job.name)}-{job.id}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
