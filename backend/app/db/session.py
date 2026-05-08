"""DB engine + session factory + lightweight schema migrations."""
from __future__ import annotations

import logging
from collections.abc import Iterator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base

logger = logging.getLogger("gpt_image2.db")


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


# Idempotent column-add migrations for SQLite. Each entry: (table, column,
# ALTER TABLE clause). Runs on startup; columns already present are skipped.
# Added on top of metadata.create_all (which only handles new tables).
ADD_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("job_items", "next_retry_at", "ALTER TABLE job_items ADD COLUMN next_retry_at DATETIME"),
    ("job_items", "output_dir",    "ALTER TABLE job_items ADD COLUMN output_dir VARCHAR(500)"),
]


def _apply_column_migrations() -> None:
    insp = inspect(engine)
    for table, column, ddl in ADD_COLUMN_MIGRATIONS:
        if not insp.has_table(table):
            continue  # create_all will handle fresh DB
        cols = {c["name"] for c in insp.get_columns(table)}
        if column in cols:
            continue
        with engine.begin() as conn:
            conn.execute(text(ddl))
        logger.info("Migrated: added %s.%s", table, column)


def init_db() -> None:
    """Create new tables, then apply additive column migrations for older DBs."""
    Base.metadata.create_all(engine)
    _apply_column_migrations()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
