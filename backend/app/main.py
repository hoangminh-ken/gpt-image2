"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cost, exports, jobs, preview, uploads, ws
from app.api import settings as settings_api
from app.config import settings
from app.core.worker_pool import WorkerPool, resume_scan
from app.db.session import init_db

logger = logging.getLogger("gpt_image2")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    removed = uploads.cleanup_old_uploads()
    if removed:
        logger.info("Cleaned %d expired upload files", removed)

    pool = WorkerPool(concurrency=settings.default_concurrency)
    enqueued = resume_scan(pool)
    if enqueued:
        logger.info("Resume scan enqueued %d items from previous run", enqueued)
    await pool.start()
    app.state.pool = pool
    logger.info("Server ready on %s:%d", settings.host, settings.port)
    try:
        yield
    finally:
        await pool.shutdown(timeout=60.0)


def create_app() -> FastAPI:
    app = FastAPI(title="gpt-image2 batch generator", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(jobs.router)
    app.include_router(preview.router)
    app.include_router(uploads.router)
    app.include_router(ws.router)
    app.include_router(cost.router)
    app.include_router(settings_api.router)
    app.include_router(exports.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "openai_configured": bool(settings.openai_api_key)}

    return app


app = create_app()
