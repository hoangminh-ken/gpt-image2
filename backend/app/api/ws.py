"""WebSocket endpoint for real-time job item updates."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from app.core.ws_broker import broker
from app.db.models import Job
from app.db.session import get_db

logger = logging.getLogger("gpt_image2.ws")

router = APIRouter(tags=["ws"])


@router.websocket("/ws/jobs/{job_id}")
async def ws_job(ws: WebSocket, job_id: int, db: Session = Depends(get_db)):
    if db.get(Job, job_id) is None:
        await ws.close(code=4404)
        return
    await ws.accept()
    await broker.subscribe(job_id, ws)
    try:
        while True:
            await ws.receive_text()  # treat any inbound as keepalive
    except WebSocketDisconnect:
        pass
    finally:
        await broker.unsubscribe(job_id, ws)
