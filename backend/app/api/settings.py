"""Settings API: read masked config + test OpenAI key."""
from __future__ import annotations

from fastapi import APIRouter
from openai import APIError, OpenAI
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


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
    default_concurrency: int
    max_ref_dimension: int
    output_dir: str
    upload_dir: str


@router.get("", response_model=SettingsOut)
def get_settings() -> SettingsOut:
    return SettingsOut(
        openai_api_key_masked=_mask(settings.openai_api_key),
        openai_admin_key_masked=_mask(settings.openai_admin_key),
        openai_api_key_set=bool(settings.openai_api_key),
        openai_admin_key_set=bool(settings.openai_admin_key),
        default_concurrency=settings.default_concurrency,
        max_ref_dimension=settings.max_ref_dimension,
        output_dir=settings.output_dir,
        upload_dir=settings.upload_dir,
    )


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
