"""Async per-item executor with retry state machine.

States: pending → running → done | failed_retryable | failed_permanent
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import settings
from app.core import openai_client
from app.core.key_manager import key_manager
from app.core.pricing import compute_cost
from app.core.retry_policy import backoff_seconds, should_retry
from app.core.ws_broker import broker
from app.db.models import CostDaily, Job, JobItem
from app.db.session import SessionLocal
from app.utils.slug import safe_filename, slugify, store_path

logger = logging.getLogger("gpt_image2.exec")


def _output_filename(item: JobItem) -> str:
    if item.output_name:
        clean = safe_filename(item.output_name)
        if clean:
            return clean if clean.lower().endswith(".png") else f"{clean}.png"
    return f"{item.row_idx:04d}-{slugify(item.prompt)}.png"


def _bump_cost_daily(db: Session, in_tokens: int, out_tokens: int, cost: Decimal) -> None:
    today = date.today().isoformat()
    row = db.get(CostDaily, (today, "local"))
    if row is None:
        db.add(
            CostDaily(
                date=today, source="local",
                input_tokens=in_tokens, output_tokens=out_tokens, cost_usd=cost,
            )
        )
    else:
        row.input_tokens += in_tokens
        row.output_tokens += out_tokens
        row.cost_usd = (row.cost_usd or Decimal("0")) + cost


def _item_to_payload(item: JobItem) -> dict:
    return {
        "id": item.id,
        "job_id": item.job_id,
        "row_idx": item.row_idx,
        "status": item.status,
        "attempts": item.attempts,
        "error": item.error,
        "output_path": item.output_path,
        "input_tokens": item.input_tokens,
        "output_tokens": item.output_tokens,
        "cost_usd": float(item.cost_usd or 0),
        "started_at": item.started_at,
        "finished_at": item.finished_at,
        "next_retry_at": item.next_retry_at,
    }


async def _publish(item: JobItem) -> None:
    await broker.publish(item.job_id, {"type": "item_update", "item": _item_to_payload(item)})


async def run_item(item_id: int) -> None:
    """Run one job item. Caller (worker pool) handles dequeuing."""
    db = SessionLocal()
    try:
        item = db.get(JobItem, item_id)
        if item is None:
            return
        # Honor pause flag at the last moment
        job = db.get(Job, item.job_id)
        if job is None or job.status in ("paused", "cancelled"):
            return

        item.status = "running"
        item.started_at = datetime.utcnow()
        item.attempts += 1
        item.error = None
        item.next_retry_at = None
        db.commit()
        await _publish(item)

        # Pick a key (round-robin across enabled keys; falls back to .env key)
        try:
            key_id, api_key = key_manager.next()
        except RuntimeError as exc:
            item.status = "failed_permanent"
            item.error = str(exc)[:1000]
            item.finished_at = datetime.utcnow()
            db.commit()
            await _publish(item)
            return

        try:
            result = await openai_client.edit_image_async(
                prompt=item.prompt, ref_paths=item.refs_json, api_key=api_key,
            )
        except Exception as exc:  # noqa: BLE001
            # If 429, mark this key as cooled-down so dispatcher skips it briefly
            status = getattr(exc, "status_code", None) or getattr(exc, "http_status", None)
            if status == 429 and key_id is not None:
                key_manager.mark_rate_limited(key_id, cooldown_seconds=60)
            logger.warning("Item %s attempt %s failed (key=%s): %s", item.id, item.attempts, key_id, exc)
            if should_retry(exc, item.attempts):
                delay = backoff_seconds(item.attempts)
                item.status = "failed_retryable"
                item.error = f"{type(exc).__name__}: {exc}"[:1000]
                item.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            else:
                item.status = "failed_permanent"
                item.error = f"{type(exc).__name__}: {exc}"[:1000]
                item.finished_at = datetime.utcnow()
            db.commit()
            await _publish(item)
            return

        key_manager.mark_used(key_id)

        # success
        job_dir = settings.output_path / str(item.job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        out_file = job_dir / _output_filename(item)
        await asyncio.to_thread(out_file.write_bytes, result.image_bytes)

        cost = compute_cost(
            result.input_tokens, result.output_tokens,
            model=settings.openai_image_model,
        )
        item.input_tokens = result.input_tokens
        item.output_tokens = result.output_tokens
        item.cost_usd = cost
        item.output_path = store_path(out_file, settings.project_root)
        item.status = "done"
        item.finished_at = datetime.utcnow()
        _bump_cost_daily(db, result.input_tokens, result.output_tokens, cost)
        db.commit()
        await _publish(item)
    finally:
        db.close()


def update_job_terminal_status(db: Session, job_id: int) -> None:
    """If all items reached a terminal state, mark job done/failed."""
    job = db.get(Job, job_id)
    if job is None or job.status in ("paused", "cancelled"):
        return
    items = db.query(JobItem).filter(JobItem.job_id == job_id).all()
    if not items:
        return
    if any(i.status in ("pending", "running", "failed_retryable") for i in items):
        return
    job.status = "done" if all(i.status == "done" for i in items) else "failed"
    job.completed_at = datetime.utcnow()
    db.commit()
