"""Cost dashboard endpoints — local aggregation + OpenAI Usage API reconcile."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.core.usage_api import UsageApiUnavailable, default_window, fetch_image_usage
from app.db.models import CostDaily
from app.db.session import get_db

router = APIRouter(prefix="/api/cost", tags=["cost"])


def _window_total(rows: list[CostDaily], start: date, end: date, source: str) -> Decimal:
    total = Decimal("0")
    for r in rows:
        if r.source != source:
            continue
        d = date.fromisoformat(r.date)
        if start <= d <= end:
            total += r.cost_usd or Decimal("0")
    return total


def _drift_pct(local: Decimal, openai_v: Decimal) -> float | None:
    if local == 0 and openai_v == 0:
        return 0.0
    if local == 0:
        return None
    return float(abs(openai_v - local) / local * 100)


@router.get("")
def cost_summary(db: Session = Depends(get_db)) -> dict:
    today = date.today()
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)

    rows = db.query(CostDaily).all()

    def windowed(start: date) -> dict:
        local = _window_total(rows, start, today, "local")
        openai_v = _window_total(rows, start, today, "openai")
        return {
            "local_usd": float(local),
            "openai_usd": float(openai_v),
            "drift_pct": _drift_pct(local, openai_v),
        }

    by_day_map: dict[str, dict] = defaultdict(lambda: {"local": 0.0, "openai": 0.0})
    for r in rows:
        d = date.fromisoformat(r.date)
        if d < month_start:
            continue
        by_day_map[r.date][r.source] = float(r.cost_usd or 0)

    by_day = sorted(
        [{"date": k, **v} for k, v in by_day_map.items()],
        key=lambda x: x["date"],
    )

    return {
        "today": windowed(today),
        "week": windowed(week_start),
        "month": windowed(month_start),
        "by_day": by_day,
        "admin_key_configured": bool(settings.openai_admin_key),
    }


@router.post("/reconcile")
async def reconcile(db: Session = Depends(get_db)) -> dict:
    if not settings.openai_admin_key:
        raise HTTPException(
            400,
            "Configure OPENAI_ADMIN_KEY in .env to enable reconcile (org admin scope required).",
        )
    start, end = default_window(30)
    try:
        buckets = await fetch_image_usage(start, end, settings.openai_admin_key)
    except UsageApiUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc

    updated = 0
    for b in buckets:
        existing = db.get(CostDaily, (b["date"], "openai"))
        if existing is None:
            db.add(CostDaily(
                date=b["date"], source="openai",
                input_tokens=b["input_tokens"],
                output_tokens=b["output_tokens"],
                cost_usd=b["cost_usd"],
            ))
        else:
            existing.input_tokens = b["input_tokens"]
            existing.output_tokens = b["output_tokens"]
            existing.cost_usd = b["cost_usd"]
        updated += 1
    db.commit()
    return {
        "updated_dates": [b["date"] for b in buckets],
        "count": updated,
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
    }
