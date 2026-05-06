"""API key dispatcher: round-robin across enabled keys with rate-limit cooldown.

Sources:
- Primary: rows in `api_keys` table (managed via Settings UI)
- Fallback: settings.openai_api_key from .env (when no rows enabled)
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

from app.config import settings
from app.db.models import ApiKey
from app.db.session import SessionLocal

logger = logging.getLogger("gpt_image2.keys")


class KeyManager:
    """Thread-safe round-robin dispatcher.

    next() returns (key_id_or_None, key_string) — id is None when falling back
    to the .env key. Caller passes the id back to mark_rate_limited / mark_used
    so per-key state is tracked.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counter = 0

    def _enabled_keys_now(self) -> list[ApiKey]:
        """Return enabled, non-cooldown keys. Each call hits the DB so changes
        from the Settings UI take effect immediately."""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            rows: list[ApiKey] = (
                db.query(ApiKey)
                .filter(ApiKey.enabled.is_(True))
                .order_by(ApiKey.id)
                .all()
            )
            return [r for r in rows if r.rate_limited_until is None or r.rate_limited_until <= now]
        finally:
            db.close()

    def next(self) -> tuple[int | None, str]:
        """Pick next available key. Falls back to settings.openai_api_key when
        no DB keys are usable. Raises if neither is available."""
        with self._lock:
            keys = self._enabled_keys_now()
            if keys:
                k = keys[self._counter % len(keys)]
                self._counter += 1
                return (k.id, k.key)

        if settings.openai_api_key:
            return (None, settings.openai_api_key)

        raise RuntimeError(
            "No API key configured. Add one via Settings → API keys, or set "
            "OPENAI_API_KEY in .env."
        )

    def mark_used(self, key_id: int | None) -> None:
        if key_id is None:
            return
        db = SessionLocal()
        try:
            row = db.get(ApiKey, key_id)
            if row is not None:
                row.last_used_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def mark_rate_limited(self, key_id: int | None, cooldown_seconds: int = 60) -> None:
        if key_id is None:
            return
        db = SessionLocal()
        try:
            row = db.get(ApiKey, key_id)
            if row is not None:
                row.rate_limited_until = datetime.utcnow() + timedelta(seconds=cooldown_seconds)
                db.commit()
                logger.info("Key %s (#%s) rate-limited for %ds", row.name, row.id, cooldown_seconds)
        finally:
            db.close()

    def total_capacity(self, per_key_concurrency: int) -> int:
        """Effective pool concurrency = enabled_keys × per_key, min per_key."""
        keys = self._enabled_keys_now()
        if not keys and settings.openai_api_key:
            return per_key_concurrency
        return max(per_key_concurrency, len(keys) * per_key_concurrency)


key_manager = KeyManager()
