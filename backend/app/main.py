"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import jobs, preview, uploads
from app.config import settings
from app.db.session import init_db

logger = logging.getLogger("gpt_image2")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    removed = uploads.cleanup_old_uploads()
    if removed:
        logger.info("Cleaned %d expired upload files", removed)
    logger.info("Server ready on %s:%d", settings.host, settings.port)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="gpt-image2 batch generator", version="0.1.0", lifespan=lifespan)
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

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "openai_configured": bool(settings.openai_api_key)}

    return app


app = create_app()
