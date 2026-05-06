"""Test fixtures: isolated SQLite + temp output dir."""
from __future__ import annotations

import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path so `import app...` works
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def tmp_workspace(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Set DB and output paths to a tmpdir for full isolation."""
    workdir = Path(tempfile.mkdtemp(prefix="gpti2-"))
    db_file = workdir / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("OUTPUT_DIR", str(workdir / "outputs"))
    monkeypatch.setenv("UPLOAD_DIR", str(workdir / "uploads"))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    # Hard isolation: redirect env file to a tmp location so no test ever
    # writes into the real backend/.env (this would clobber real API keys).
    monkeypatch.setenv("GPT_IMAGE2_ENV_FILE", str(workdir / "_test.env"))
    # Force re-import of settings + engine
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]
    yield workdir
    shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture
def sample_png(tmp_workspace: Path) -> Path:
    """A tiny valid PNG for tests."""
    from PIL import Image

    p = tmp_workspace / "ref.png"
    Image.new("RGB", (32, 32), (200, 100, 50)).save(p)
    return p
