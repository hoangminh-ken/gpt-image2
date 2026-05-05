"""Phase 1 synchronous worker. Runs a job item-by-item via FastAPI BackgroundTasks.

Replaced by async pool in Phase 2.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import settings
from app.core import openai_client
from app.core.pricing import compute_cost
from app.db.models import CostDaily, Job, JobItem
from app.db.session import SessionLocal
from app.utils.slug import safe_filename, slugify, store_path


def _output_filename(item: JobItem) -> str:
    if item.output_name:
        clean = safe_filename(item.output_name)
        if clean:
            base = clean
            if not base.lower().endswith(".png"):
                base += ".png"
            return base
    return f"{item.row_idx:04d}-{slugify(item.prompt)}.png"


def _bump_cost_daily(db: Session, in_tokens: int, out_tokens: int, cost: Decimal) -> None:
    today = date.today().isoformat()
    row = db.get(CostDaily, (today, "local"))
    if row is None:
        row = CostDaily(
            date=today,
            source="local",
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cost_usd=cost,
        )
        db.add(row)
    else:
        row.input_tokens += in_tokens
        row.output_tokens += out_tokens
        row.cost_usd = (row.cost_usd or Decimal("0")) + cost


def _process_item(db: Session, job_id: int, item: JobItem) -> None:
    item.status = "running"
    item.started_at = datetime.utcnow()
    item.attempts += 1
    db.commit()

    try:
        result = openai_client.edit_image(prompt=item.prompt, ref_paths=item.refs_json)
    except Exception as exc:  # noqa: BLE001
        item.status = "failed_permanent"
        item.error = f"{type(exc).__name__}: {exc}"[:1000]
        item.finished_at = datetime.utcnow()
        db.commit()
        return

    job_dir = settings.output_path / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    out_file = job_dir / _output_filename(item)
    out_file.write_bytes(result.image_bytes)

    cost = compute_cost(result.input_tokens, result.output_tokens)
    item.input_tokens = result.input_tokens
    item.output_tokens = result.output_tokens
    item.cost_usd = cost
    item.output_path = store_path(out_file, settings.project_root)
    item.status = "done"
    item.finished_at = datetime.utcnow()

    _bump_cost_daily(db, result.input_tokens, result.output_tokens, cost)
    db.commit()


def run_job(job_id: int) -> None:
    """Run all pending items in a job sequentially. Called by BackgroundTasks."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        job.status = "running"
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()

        items = (
            db.query(JobItem)
            .filter(JobItem.job_id == job_id, JobItem.status == "pending")
            .order_by(JobItem.row_idx)
            .all()
        )
        for item in items:
            _process_item(db, job_id, item)

        # mark job done if no failures linger
        remaining = (
            db.query(JobItem)
            .filter(
                JobItem.job_id == job_id,
                JobItem.status.in_(("pending", "running")),
            )
            .count()
        )
        job.status = "done" if remaining == 0 else "failed"
        job.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
