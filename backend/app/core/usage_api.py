"""OpenAI Organization Usage API client for cost reconcile (Phase 5).

Endpoint: GET https://api.openai.com/v1/organization/usage/images
Requires admin/org-scoped key (OPENAI_ADMIN_KEY).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from app.config import settings
from app.core.pricing import compute_cost

logger = logging.getLogger("gpt_image2.usage")

USAGE_URL = "https://api.openai.com/v1/organization/usage/images"


class UsageApiUnavailable(RuntimeError):
    pass


async def fetch_image_usage(start_unix: int, end_unix: int, admin_key: str) -> list[dict]:
    """Fetch daily image usage buckets, returns list of dicts:
    {date: 'YYYY-MM-DD', input_tokens, output_tokens, num_requests, cost_usd}
    """
    if not admin_key:
        raise UsageApiUnavailable("OPENAI_ADMIN_KEY not configured")

    params = {
        "start_time": start_unix,
        "end_time": end_unix,
        "bucket_width": "1d",
        "limit": 31,
    }
    headers = {"Authorization": f"Bearer {admin_key}"}

    out: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        cursor: str | None = None
        for _ in range(20):  # safety bound on pagination
            if cursor:
                params["page"] = cursor
            resp = await client.get(USAGE_URL, params=params, headers=headers)
            if resp.status_code in (401, 403):
                raise UsageApiUnavailable(
                    f"Usage API access denied ({resp.status_code}). "
                    "Verify OPENAI_ADMIN_KEY has org admin scope."
                )
            resp.raise_for_status()
            payload = resp.json()
            for bucket in payload.get("data", []):
                start_ts = bucket.get("start_time")
                if start_ts is None:
                    continue
                bucket_date = datetime.fromtimestamp(start_ts, tz=timezone.utc).date().isoformat()
                in_tokens = 0
                out_tokens = 0
                num_req = 0
                for r in bucket.get("results", []):
                    in_tokens += int(r.get("input_tokens", 0))
                    out_tokens += int(r.get("output_tokens", 0))
                    num_req += int(r.get("num_model_requests", 0))
                cost: Decimal = compute_cost(
                    in_tokens, out_tokens, model=settings.openai_image_model,
                )
                out.append({
                    "date": bucket_date,
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens,
                    "num_requests": num_req,
                    "cost_usd": cost,
                })
            cursor = payload.get("next_page")
            if not cursor:
                break
    return out


def default_window(days: int = 30) -> tuple[int, int]:
    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=days)
    return int(start.timestamp()), int(end.timestamp())
