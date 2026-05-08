"""API keys management: store multiple keys, distribute requests round-robin."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import APIError, OpenAI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import ApiKey
from app.db.session import get_db


def _resize_pool(request: Request) -> None:
    """Hot-grow worker pool after key state changes (no restart needed)."""
    pool = getattr(request.app.state, "pool", None)
    if pool is not None:
        pool.ensure_capacity()


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 14:
        return "***"
    return f"{value[:7]}…{value[-4:]}"


router = APIRouter(prefix="/api/keys", tags=["api-keys"])


class KeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    key: str = Field(min_length=10)


class KeyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    enabled: bool | None = None


class KeyOut(BaseModel):
    id: int
    name: str
    key_masked: str
    enabled: bool
    last_used_at: datetime | None
    rate_limited_until: datetime | None
    created_at: datetime


def _to_out(k: ApiKey) -> KeyOut:
    return KeyOut(
        id=k.id, name=k.name, key_masked=_mask(k.key), enabled=k.enabled,
        last_used_at=k.last_used_at, rate_limited_until=k.rate_limited_until,
        created_at=k.created_at,
    )


@router.get("", response_model=list[KeyOut])
def list_keys(db: Session = Depends(get_db)) -> list[KeyOut]:
    rows = db.query(ApiKey).order_by(ApiKey.id).all()
    return [_to_out(k) for k in rows]


@router.post("", response_model=KeyOut, status_code=201)
def create_key(payload: KeyCreate, request: Request, db: Session = Depends(get_db)) -> KeyOut:
    k = ApiKey(name=payload.name.strip(), key=payload.key.strip(), enabled=True)
    db.add(k)
    db.commit()
    db.refresh(k)
    _resize_pool(request)
    return _to_out(k)


@router.put("/{key_id}", response_model=KeyOut)
def update_key(key_id: int, payload: KeyUpdate, request: Request, db: Session = Depends(get_db)) -> KeyOut:
    k = db.get(ApiKey, key_id)
    if k is None:
        raise HTTPException(404, "Key not found")
    if payload.name is not None:
        k.name = payload.name.strip()
    if payload.enabled is not None:
        k.enabled = payload.enabled
    db.commit()
    db.refresh(k)
    if payload.enabled is True:
        _resize_pool(request)
    return _to_out(k)


@router.delete("/{key_id}", status_code=204)
def delete_key(key_id: int, db: Session = Depends(get_db)) -> None:
    k = db.get(ApiKey, key_id)
    if k is None:
        raise HTTPException(404, "Key not found")
    db.delete(k)
    db.commit()


@router.post("/{key_id}/test")
def test_key(key_id: int, db: Session = Depends(get_db)) -> dict:
    k = db.get(ApiKey, key_id)
    if k is None:
        raise HTTPException(404, "Key not found")
    try:
        client = OpenAI(api_key=k.key)
        models = client.models.list()
        return {"ok": True, "models_sample": [m.id for m in list(models)[:3]]}
    except APIError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
