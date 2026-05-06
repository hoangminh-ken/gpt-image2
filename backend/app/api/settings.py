"""Settings API: read masked config, edit .env, test OpenAI key."""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from openai import APIError, OpenAI
from pydantic import BaseModel, Field

from app.config import settings
from app.paths import env_example_template, env_file_path

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Live updates take effect for these (used per-request via settings singleton).
LIVE_FIELDS = {"openai_api_key", "openai_admin_key", "openai_image_model", "max_ref_dimension"}
# These need server restart (worker pool reads at startup).
RESTART_FIELDS = {"default_concurrency"}


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 14:
        return "***"
    return f"{value[:7]}…{value[-4:]}"


class SettingsOut(BaseModel):
    openai_api_key_masked: str
    openai_admin_key_masked: str
    openai_api_key_set: bool
    openai_admin_key_set: bool
    openai_image_model: str
    default_concurrency: int
    max_ref_dimension: int
    output_dir: str
    upload_dir: str
    env_file_path: str
    restart_required_for: list[str] = []


class SettingsUpdate(BaseModel):
    openai_api_key: str | None = Field(default=None, description="empty string = clear; null = no change")
    openai_admin_key: str | None = None
    openai_image_model: str | None = None
    default_concurrency: int | None = Field(default=None, ge=1, le=20)
    max_ref_dimension: int | None = Field(default=None, ge=512, le=4096)


def _read_env_file() -> str:
    path = env_file_path()
    if not path.exists():
        return env_example_template()
    return path.read_text(encoding="utf-8")


def _upsert_env_line(content: str, key: str, value: str) -> str:
    """Replace existing KEY=... line, or append if absent. Preserves comments/order."""
    pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
    new_line = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(new_line, content)
    if content and not content.endswith("\n"):
        content += "\n"
    return content + new_line + "\n"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _build_out() -> SettingsOut:
    return SettingsOut(
        openai_api_key_masked=_mask(settings.openai_api_key),
        openai_admin_key_masked=_mask(settings.openai_admin_key),
        openai_api_key_set=bool(settings.openai_api_key),
        openai_admin_key_set=bool(settings.openai_admin_key),
        openai_image_model=settings.openai_image_model,
        default_concurrency=settings.default_concurrency,
        max_ref_dimension=settings.max_ref_dimension,
        output_dir=settings.output_dir,
        upload_dir=settings.upload_dir,
        env_file_path=str(env_file_path()),
    )


@router.get("", response_model=SettingsOut)
def get_settings() -> SettingsOut:
    return _build_out()


@router.put("", response_model=SettingsOut)
def update_settings(payload: SettingsUpdate) -> SettingsOut:
    """Update .env in place. Mutates settings singleton for LIVE_FIELDS so changes
    take effect immediately. RESTART_FIELDS are persisted but require restart.
    """
    changes: dict[str, str] = {}
    restart_needed: list[str] = []

    def stage(key: str, value):
        if value is None:
            return
        env_key = key.upper()
        # Empty string = clear in env file
        changes[env_key] = "" if (isinstance(value, str) and value == "") else str(value)
        # Mutate live in-memory for fields that don't need restart
        if key in LIVE_FIELDS:
            try:
                cast = type(getattr(settings, key))
                setattr(settings, key, cast(value) if value != "" else cast())
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(400, f"Invalid value for {key}: {exc}") from exc
        elif key in RESTART_FIELDS:
            restart_needed.append(key)

    stage("openai_api_key", payload.openai_api_key)
    stage("openai_admin_key", payload.openai_admin_key)
    stage("openai_image_model", payload.openai_image_model)
    stage("default_concurrency", payload.default_concurrency)
    stage("max_ref_dimension", payload.max_ref_dimension)

    if not changes:
        return _build_out()

    # Persist to .env
    content = _read_env_file()
    for k, v in changes.items():
        content = _upsert_env_line(content, k, v)
    _atomic_write(env_file_path(), content)

    out = _build_out()
    out.restart_required_for = restart_needed
    return out


@router.get("/test-key")
def test_key() -> dict:
    if not settings.openai_api_key:
        return {"ok": False, "error": "OPENAI_API_KEY not configured"}
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        models = client.models.list()
        names = [m.id for m in list(models)[:5]]
        return {"ok": True, "models_sample": names}
    except APIError as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
