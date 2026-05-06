"""Prompt library: save reusable prompts, list/select on New Job page."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Prompt
from app.db.session import get_db

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


class PromptIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


class PromptOut(BaseModel):
    id: int
    name: str
    content: str
    used_count: int
    created_at: datetime
    updated_at: datetime


def _to_out(p: Prompt) -> PromptOut:
    return PromptOut(
        id=p.id, name=p.name, content=p.content,
        used_count=p.used_count, created_at=p.created_at, updated_at=p.updated_at,
    )


@router.get("", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db)) -> list[PromptOut]:
    rows = db.query(Prompt).order_by(Prompt.used_count.desc(), Prompt.updated_at.desc()).all()
    return [_to_out(p) for p in rows]


@router.post("", response_model=PromptOut, status_code=201)
def create_prompt(payload: PromptIn, db: Session = Depends(get_db)) -> PromptOut:
    p = Prompt(name=payload.name.strip(), content=payload.content)
    db.add(p)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A prompt with this name already exists") from exc
    db.refresh(p)
    return _to_out(p)


@router.put("/{prompt_id}", response_model=PromptOut)
def update_prompt(prompt_id: int, payload: PromptIn, db: Session = Depends(get_db)) -> PromptOut:
    p = db.get(Prompt, prompt_id)
    if p is None:
        raise HTTPException(404, "Prompt not found")
    p.name = payload.name.strip()
    p.content = payload.content
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Name conflicts with another prompt") from exc
    db.refresh(p)
    return _to_out(p)


@router.delete("/{prompt_id}", status_code=204)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)) -> None:
    p = db.get(Prompt, prompt_id)
    if p is None:
        raise HTTPException(404, "Prompt not found")
    db.delete(p)
    db.commit()


@router.post("/{prompt_id}/use", response_model=PromptOut)
def increment_use(prompt_id: int, db: Session = Depends(get_db)) -> PromptOut:
    p = db.get(Prompt, prompt_id)
    if p is None:
        raise HTTPException(404, "Prompt not found")
    p.used_count += 1
    db.commit()
    db.refresh(p)
    return _to_out(p)
