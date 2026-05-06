"""DB engine + session factory."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base


def _make_engine():
    url = settings.database_url
    if url.startswith("sqlite:///"):
        rel = url[len("sqlite:///"):]
        # Resolve path against settings.project_root (= user_data_root in frozen mode,
        # repo root in dev). ":" check guards Windows drive-letter absolute paths.
        if not rel.startswith("/") and (len(rel) < 2 or rel[1] != ":"):
            abs_path = settings.project_root / rel
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{abs_path}"
    eng = create_engine(url, future=True, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _enable_wal(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables (Phase 1 — alembic added in Phase 2)."""
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
