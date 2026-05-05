"""Upload endpoint tests."""
from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image


def _png_buf() -> bytes:
    img = Image.new("RGB", (16, 16), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_one_png(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/uploads/refs",
        files=[("files", ("a.png", _png_buf(), "image/png"))],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["files"]) == 1
    assert body["files"][0]["name"] == "a.png"
    assert Path(body["files"][0]["abs_path"]).is_file()


def test_upload_rejects_non_image(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/uploads/refs",
        files=[("files", ("evil.txt", b"hello", "text/plain"))],
    )
    assert resp.status_code == 415


def test_upload_too_many(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    # MAX_FILES = 16 → 17 files should fail
    files = [("files", (f"a{i}.png", _png_buf(), "image/png")) for i in range(17)]
    resp = client.post("/api/uploads/refs", files=files)
    assert resp.status_code == 400


def test_preview_nonexistent_returns_404(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    # Image extension under tracked roots but file doesn't exist
    assert client.get("/api/preview/outputs/none/missing.png").status_code == 404


def test_preview_rejects_non_image_outside(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    client = TestClient(app)
    # Absolute path outside allowed roots, no image extension
    resp = client.get("/api/preview/C:/Windows/System32/notepad.exe")
    assert resp.status_code in (403, 404)
