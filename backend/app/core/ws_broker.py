"""In-memory pub/sub for WebSocket broadcasts per job_id."""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from starlette.websockets import WebSocket

logger = logging.getLogger("gpt_image2.ws")


class WsBroker:
    def __init__(self) -> None:
        self._subs: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, job_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._subs[job_id].add(ws)

    async def unsubscribe(self, job_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self._subs.get(job_id, set()).discard(ws)
            if not self._subs.get(job_id):
                self._subs.pop(job_id, None)

    async def publish(self, job_id: int, payload: dict) -> None:
        text = json.dumps(payload, default=str)
        async with self._lock:
            sockets = list(self._subs.get(job_id, ()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(text)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._subs.get(job_id, set()).discard(ws)


broker = WsBroker()
