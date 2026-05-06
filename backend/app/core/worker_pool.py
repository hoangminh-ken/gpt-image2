"""Async worker pool with semaphore + scheduler for retry timing."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.config import settings
from app.core.executor import run_item, update_job_terminal_status
from app.core.key_manager import key_manager
from app.db.models import Job, JobItem
from app.db.session import SessionLocal

logger = logging.getLogger("gpt_image2.pool")


class WorkerPool:
    def __init__(self, concurrency: int | None = None) -> None:
        per_key = concurrency or settings.default_concurrency
        # Total parallel = enabled_keys × per_key (1 key worth if no DB keys)
        self.concurrency = key_manager.total_capacity(per_key)
        self.queue: asyncio.Queue[int] = asyncio.Queue()
        self._consumers: list[asyncio.Task] = []
        self._scheduler: asyncio.Task | None = None
        self._stopping = asyncio.Event()

    async def start(self) -> None:
        for i in range(self.concurrency):
            self._consumers.append(asyncio.create_task(self._consume(i), name=f"worker-{i}"))
        self._scheduler = asyncio.create_task(self._schedule_retries(), name="retry-scheduler")
        logger.info("Worker pool started with %d consumers", self.concurrency)

    async def shutdown(self, timeout: float = 60.0) -> None:
        self._stopping.set()
        # cancel scheduler immediately
        if self._scheduler:
            self._scheduler.cancel()
        # let queue drain or timeout
        try:
            await asyncio.wait_for(self.queue.join(), timeout=timeout)
        except TimeoutError:
            logger.warning("Pool shutdown: queue join timed out")
        for c in self._consumers:
            c.cancel()
        await asyncio.gather(*self._consumers, return_exceptions=True)
        if self._scheduler:
            await asyncio.gather(self._scheduler, return_exceptions=True)
        logger.info("Worker pool stopped")

    def enqueue(self, item_id: int) -> None:
        self.queue.put_nowait(item_id)

    def enqueue_many(self, item_ids: list[int]) -> None:
        for i in item_ids:
            self.queue.put_nowait(i)

    async def _consume(self, idx: int) -> None:
        while not self._stopping.is_set():
            try:
                item_id = await self.queue.get()
            except asyncio.CancelledError:
                break
            try:
                # Check pause flag right before running
                if self._is_job_paused(item_id):
                    # Re-enqueue later? no — when resumed we re-scan DB and enqueue.
                    pass
                else:
                    await run_item(item_id)
                    self._mark_job_terminal(item_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Worker %d crashed on item %s: %s", idx, item_id, exc)
            finally:
                self.queue.task_done()

    @staticmethod
    def _is_job_paused(item_id: int) -> bool:
        db = SessionLocal()
        try:
            item = db.get(JobItem, item_id)
            if item is None:
                return True  # treat missing as skip
            job = db.get(Job, item.job_id)
            return job is not None and job.status in ("paused", "cancelled")
        finally:
            db.close()

    @staticmethod
    def _mark_job_terminal(item_id: int) -> None:
        db = SessionLocal()
        try:
            item = db.get(JobItem, item_id)
            if item is not None:
                update_job_terminal_status(db, item.job_id)
        finally:
            db.close()

    async def _schedule_retries(self) -> None:
        """Poll DB for items whose next_retry_at has passed; re-enqueue."""
        while not self._stopping.is_set():
            try:
                db = SessionLocal()
                try:
                    now = datetime.utcnow()
                    rows = (
                        db.query(JobItem)
                        .join(Job, Job.id == JobItem.job_id)
                        .filter(
                            JobItem.status == "failed_retryable",
                            JobItem.next_retry_at.isnot(None),
                            JobItem.next_retry_at <= now,
                            Job.status == "running",
                        )
                        .all()
                    )
                    for r in rows:
                        r.status = "pending"
                        r.next_retry_at = None
                    if rows:
                        db.commit()
                        for r in rows:
                            self.enqueue(r.id)
                        logger.info("Scheduler re-enqueued %d retry items", len(rows))
                finally:
                    db.close()
            except Exception as exc:  # noqa: BLE001
                logger.exception("Retry scheduler error: %s", exc)
            await asyncio.sleep(1.0)


def resume_scan(pool: WorkerPool) -> int:
    """At server start: mark in-flight items as failed_retryable, enqueue pending ones."""
    db = SessionLocal()
    try:
        # 1. items left as 'running' from previous process → failed_retryable
        in_flight = db.query(JobItem).filter(JobItem.status == "running").all()
        for it in in_flight:
            it.status = "failed_retryable"
            it.next_retry_at = datetime.utcnow()
        # 2. enqueue pending + failed_retryable for any non-paused job
        ids = (
            db.query(JobItem.id)
            .join(Job, Job.id == JobItem.job_id)
            .filter(
                JobItem.status.in_(("pending", "failed_retryable")),
                Job.status.in_(("running", "pending")),
            )
            .all()
        )
        # promote any 'pending' job that has work to 'running'
        running_jobs = (
            db.query(Job)
            .filter(Job.status == "pending")
            .all()
        )
        for j in running_jobs:
            j.status = "running"
        db.commit()
        item_ids = [row[0] for row in ids]
        for iid in item_ids:
            pool.enqueue(iid)
        return len(item_ids)
    finally:
        db.close()
