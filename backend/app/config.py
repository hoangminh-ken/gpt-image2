"""Application config loaded from .env."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.paths import env_file_path, is_frozen, user_data_root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(env_file_path()), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_admin_key: str = ""
    # Model — keep as alias 'gpt-image-2'; can pin to a snapshot like 'gpt-image-2-2026-04-21'
    openai_image_model: str = "gpt-image-2"

    database_url: str = "sqlite:///data/app.db"
    output_dir: str = "outputs"
    upload_dir: str = "data/uploads"

    default_concurrency: int = 5
    max_ref_dimension: int = 2048

    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def project_root(self) -> Path:
        # Used as the data root: dev = repo root, frozen = APPDATA/gpt-image2
        return user_data_root() if is_frozen() else Path(__file__).resolve().parents[2]

    def _resolve_dir(self, value: str) -> Path:
        p = Path(value)
        if not p.is_absolute():
            p = self.project_root / p
        p = p.resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def output_path(self) -> Path:
        return self._resolve_dir(self.output_dir)

    @property
    def upload_path(self) -> Path:
        return self._resolve_dir(self.upload_dir)

    @property
    def data_path(self) -> Path:
        return self._resolve_dir("data")


settings = Settings()
