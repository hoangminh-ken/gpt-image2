"""Job endpoints: create (Mode A), list, detail."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.worker_sync import run_job
from app.db.models import Job, JobItem
from app.db.session import get_db
from app.parsers.template import build_items

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateTemplateJob(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    mode: Literal["template"]
    template_prompt: str = Field(min_length=1)
    ref_paths: list[str] = Field(min_length=1)


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
        id=job.id,
        name=job.name,
        mode=job.mode,
        status=job.status,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        total=len(items),
        done=done,
        failed=failed,
    )


def _item_to_out(item: JobItem) -> ItemOut:
    return ItemOut(
        id=item.id,
        row_idx=item.row_idx,
        prompt=item.prompt,
        refs=item.refs_json or [],
        output_name=item.output_name,
        status=item.status,
        attempts=item.attempts,
        error=item.error,
        output_path=item.output_path,
        input_tokens=item.input_tokens,
        output_tokens=item.output_tokens,
        cost_usd=float(item.cost_usd or 0),
        started_at=item.started_at,
        finished_at=item.finished_at,
    )


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    payload: CreateTemplateJob,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JobOut:
    specs = build_items(payload.template_prompt, payload.ref_paths)
    job = Job(name=payload.name, mode=payload.mode, status="pending", config_json={})
    db.add(job)
    db.flush()

    for s in specs:
        db.add(
            JobItem(
                job_id=job.id,
                row_idx=s.row_idx,
                prompt=s.prompt,
                refs_json=s.refs,
                output_name=s.output_name,
                status="pending",
            )
        )
    db.commit()
    db.refresh(job)

    bg.add_task(run_job, job.id)
    return _job_to_out(job, list(job.items))


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    jobs = db.query(Job).order_by(Job.created_at.desc()).all()
    return [_job_to_out(j, list(j.items)) for j in jobs]


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDetail:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    items = sorted(job.items, key=lambda i: i.row_idx)
    base = _job_to_out(job, items)
    return JobDetail(**base.model_dump(), items=[_item_to_out(i) for i in items])
