"""Retry policy: classify exceptions, compute backoff."""
from __future__ import annotations

import random

MAX_ATTEMPTS = 5
BASE_DELAY_SEC = 1.0
MAX_DELAY_SEC = 16.0


def is_retryable(exc: BaseException) -> bool:
    """Decide whether to retry given the exception type / status."""
    name = type(exc).__name__
    if name in {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}:
        return True

    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "http_status", None)
    if isinstance(status, int):
        if status == 429 or 500 <= status < 600:
            return True
        if 400 <= status < 500:
            return False
    return False


def backoff_seconds(attempt: int) -> float:
    """Exponential backoff with ±25% jitter. attempt is 1-indexed."""
    delay = min(BASE_DELAY_SEC * (2 ** max(0, attempt - 1)), MAX_DELAY_SEC)
    jitter = 1.0 + random.uniform(-0.25, 0.25)
    return delay * jitter


def should_retry(exc: BaseException, attempt: int) -> bool:
    return attempt < MAX_ATTEMPTS and is_retryable(exc)
