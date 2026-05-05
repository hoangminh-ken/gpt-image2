"""Job endpoints: create (Mode A), list, detail, pause/resume/cancel, item retry."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.executor import update_job_terminal_status
from app.db.models import Job, JobItem
from app.db.session import get_db
from app.parsers.excel import parse_excel
from app.parsers.template import build_items

EXCEL_MAX_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateTemplateJob(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mode: Literal["template"]
    template_prompt: str = Field(min_length=1)
    ref_paths: list[str] = Field(min_length=1)


class ExcelRowIn(BaseModel):
    prompt: str
    refs: list[str]
    output_name: str | None = None


class CreateExcelJob(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mode: Literal["excel"]
    rows: list[ExcelRowIn] = Field(min_length=1)
    skip_invalid: bool = False


class ItemOut(BaseModel):
    id: int
    row_idx: int
    prompt: str
    refs: list[str]
    output_name: str | None
    status: str
    attempts: int
    error: str | None
    output_path: str | None
    input_tokens: int
    output_tokens: int
    cost_usd: float
    started_at: datetime | None
    finished_at: datetime | None
    next_retry_at: datetime | None


class JobOut(BaseModel):
    id: int
    name: str
    mode: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    total: int
    done: int
    failed: int


class JobDetail(JobOut):
    items: list[ItemOut]


def _job_to_out(job: Job, items: list[JobItem]) -> JobOut:
    done = sum(1 for i in items if i.status == "done")
    failed = sum(1 for i in items if i.status.startswith("failed"))
    return JobOut(
        id=job.id, name=job.name, mode=job.mode, status=job.status,
        created_at=job.created_at, started_at=job.started_at,
        completed_at=job.completed_at,
        total=len(items), done=done, failed=failed,
    )


def _item_to_out(item: JobItem) -> ItemOut:
    return ItemOut(
        id=item.id, row_idx=item.row_idx, prompt=item.prompt,
        refs=item.refs_json or [], output_name=item.output_name,
        status=item.status, attempts=item.attempts, error=item.error,
        output_path=item.output_path,
        input_tokens=item.input_tokens, output_tokens=item.output_tokens,
        cost_usd=float(item.cost_usd or 0),
        started_at=item.started_at, finished_at=item.finished_at,
        next_retry_at=item.next_retry_at,
    )


def _create_job_with_items(
    db: Session, request: Request, name: str, mode: str,
    items_data: list[tuple[int, str, list[str], str | None]],
) -> Job:
    job = Job(name=name, mode=mode, status="running", config_json={})
    job.started_at = datetime.utcnow()
    db.add(job)
    db.flush()
    item_ids = []
    for row_idx, prompt, refs, output_name in items_data:
        item = JobItem(
            job_id=job.id, row_idx=row_idx, prompt=prompt,
            refs_json=refs, output_name=output_name, status="pending",
        )
        db.add(item)
        db.flush()
        item_ids.append(item.id)
    db.commit()
    db.refresh(job)
    pool = getattr(request.app.state, "pool", None)
    if pool is not None:
        pool.enqueue_many(item_ids)
    return job


@router.post("", response_model=JobOut, status_code=201)
def create_job(payload: CreateTemplateJob, request: Request, db: Session = Depends(get_db)):
    specs = build_items(payload.template_prompt, payload.ref_paths)
    items_data = [(s.row_idx, s.prompt, s.refs, s.output_name) for s in specs]
    job = _create_job_with_items(db, request, payload.name, payload.mode, items_data)
    return _job_to_out(job, list(job.items))


@router.post("/excel", response_model=JobOut, status_code=201)
def create_excel_job(payload: CreateExcelJob, request: Request, db: Session = Depends(get_db)):
    valid_rows = [r for r in payload.rows if r.prompt.strip() and r.refs]
    if len(valid_rows) != len(payload.rows) and not payload.skip_invalid:
        raise HTTPException(
            400,
            f"{len(payload.rows) - len(valid_rows)} invalid rows; pass skip_invalid=true to proceed",
        )
    if not valid_rows:
        raise HTTPException(400, "No valid rows to create job from")
    items_data = [
        (i, r.prompt.strip(), [p.strip() for p in r.refs if p.strip()], r.output_name or None)
        for i, r in enumerate(valid_rows)
    ]
    job = _create_job_with_items(db, request, payload.name, payload.mode, items_data)
    return _job_to_out(job, list(job.items))


@router.post("/parse-excel")
async def parse_excel_endpoint(file: UploadFile):
    data = await file.read(EXCEL_MAX_BYTES + 1)
    if len(data) > EXCEL_MAX_BYTES:
        raise HTTPException(413, "File exceeds 10MB")
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(415, "Only .xlsx/.xlsm supported")
    return parse_excel(data).to_dict()


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [_job_to_out(j, list(j.items)) for j in jobs]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    items = sorted(job.items, key=lambda i: i.row_idx)
    base = _job_to_out(job, items)
    return JobDetail(**base.model_dump(), items=[_item_to_out(i) for i in items])


@router.post("/{job_id}/pause", response_model=JobOut)
def pause_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status not in ("running", "pending"):
        raise HTTPException(409, f"Cannot pause job in status '{job.status}'")
    job.status = "paused"
    job.paused_at = datetime.utcnow()
    db.commit()
    return _job_to_out(job, list(job.items))


@router.post("/{job_id}/resume", response_model=JobOut)
def resume_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status != "paused":
        raise HTTPException(409, f"Cannot resume job in status '{job.status}'")
    job.status = "running"
    job.paused_at = None
    items = (
        db.query(JobItem)
        .filter(JobItem.job_id == job_id, JobItem.status.in_(("pending", "failed_retryable")))
        .all()
    )
    for it in items:
        it.next_retry_at = None
        if it.status == "failed_retryable":
            it.status = "pending"
    db.commit()
    pool = getattr(request.app.state, "pool", None)
    if pool is not None and items:
        pool.enqueue_many([i.id for i in items])
    # If nothing left to do, settle terminal status now
    update_job_terminal_status(db, job_id)
    db.refresh(job)
    return _job_to_out(job, list(job.items))


@router.post("/{job_id}/cancel", response_model=JobOut)
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status in ("done", "cancelled"):
        return _job_to_out(job, list(job.items))
    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    db.query(JobItem).filter(
        JobItem.job_id == job_id,
        JobItem.status.in_(("pending", "failed_retryable")),
    ).update({"status": "cancelled"}, synchronize_session=False)
    db.commit()
    return _job_to_out(job, list(job.items))


@router.post("/{job_id}/items/{item_id}/retry", response_model=ItemOut)
def retry_item(job_id: int, item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.get(JobItem, item_id)
    if item is None or item.job_id != job_id:
        raise HTTPException(404, "Item not found")
    if item.status not in ("failed_permanent", "failed_retryable", "cancelled"):
        raise HTTPException(409, f"Cannot retry item in status '{item.status}'")
    item.status = "pending"
    item.attempts = 0
    item.error = None
    item.next_retry_at = None
    job = db.get(Job, job_id)
    if job and job.status in ("done", "failed", "cancelled"):
        job.status = "running"
        job.completed_at = None
    db.commit()
    pool = getattr(request.app.state, "pool", None)
    if pool is not None:
        pool.enqueue(item.id)
    return _item_to_out(item)
