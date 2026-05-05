"""Application config loaded from .env."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_admin_key: str = ""

    database_url: str = "sqlite:///data/app.db"
    output_dir: str = "outputs"
    upload_dir: str = "data/uploads"

    default_concurrency: int = 5
    max_ref_dimension: int = 2048

    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

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
