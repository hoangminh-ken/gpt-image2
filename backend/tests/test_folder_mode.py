"""Mode C (Folder Walker) tests."""
from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image


def _png(p: Path, color=(10, 20, 30)) -> None:
    Image.new("RGB", (32, 32), color).save(p)


def _mk_tree(root: Path) -> None:
    """Build sample tree:
        root/
        ├── set-a/  (2 images)
        ├── set-b/  (1 image)
        └── empty/  (no images)
    """
    (root / "set-a").mkdir()
    _png(root / "set-a" / "a1.png")
    _png(root / "set-a" / "a2.jpg")
    (root / "set-b").mkdir()
    _png(root / "set-b" / "b1.png")
    (root / "empty").mkdir()


def test_scan_folder_basic(tmp_workspace: Path):
    from app.main import create_app
    parent = tmp_workspace / "shoot"
    parent.mkdir()
    _mk_tree(parent)

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/jobs/scan-folder", json={
            "parent_dir": str(parent), "output_subfolder": "generated", "skip_existing": True,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_images"] == 3
        assert d["total_to_run"] == 3
        # Empty folder excluded
        names = [s["name"] for s in d["subfolders"]]
        assert sorted(names) == ["set-a", "set-b"]


def test_scan_folder_skips_existing(tmp_workspace: Path):
    from app.main import create_app
    parent = tmp_workspace / "shoot"
    parent.mkdir()
    _mk_tree(parent)
    # Pre-create one output → should be skipped
    out = parent / "set-a" / "generated"
    out.mkdir()
    _png(out / "a1.png")

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/jobs/scan-folder", json={
            "parent_dir": str(parent), "output_subfolder": "generated", "skip_existing": True,
        })
        d = r.json()
        # 3 images total, 1 already exists → 2 to run
        assert d["total_to_run"] == 2
        a = next(s for s in d["subfolders"] if s["name"] == "set-a")
        assert a["skipped_existing"] == 1


def test_scan_folder_invalid_path(tmp_workspace: Path):
    from app.main import create_app
    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/jobs/scan-folder", json={
            "parent_dir": str(tmp_workspace / "nope"),
        })
        assert r.status_code == 400


def test_create_folder_job_writes_to_subfolder(tmp_workspace: Path):
    """End-to-end: items get correct output_dir; executor writes there."""
    import time

    from app.core import openai_client
    from app.main import create_app
    parent = tmp_workspace / "shoot"
    parent.mkdir()
    _mk_tree(parent)

    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(buf, format="PNG")
    fake = openai_client.EditResult(image_bytes=buf.getvalue(), input_tokens=10, output_tokens=5)

    app = create_app()
    with patch("app.core.executor.openai_client.edit_image_async", new=AsyncMock(return_value=fake)), TestClient(app) as client:
        r = client.post("/api/jobs/folder", json={
            "name": "folder-job", "mode": "folder",
            "parent_dir": str(parent), "template_prompt": "test prompt",
            "output_subfolder": "generated",
        })
        assert r.status_code == 201, r.text
        job_id = r.json()["id"]

        deadline = time.time() + 8
        while time.time() < deadline:
            d = client.get(f"/api/jobs/{job_id}").json()
            if d["status"] in ("done", "failed"):
                break
            time.sleep(0.1)
        assert d["status"] == "done", d
        assert d["done"] == 3

        # Verify files actually written into each subfolder's `generated/`
        assert (parent / "set-a" / "generated" / "a1.png").is_file()
        assert (parent / "set-a" / "generated" / "a2.png").is_file()  # .jpg → output as .png
        assert (parent / "set-b" / "generated" / "b1.png").is_file()


def test_folder_job_no_images(tmp_workspace: Path):
    from app.main import create_app
    parent = tmp_workspace / "empty-shoot"
    parent.mkdir()
    (parent / "subdir").mkdir()  # no images inside

    app = create_app()
    with TestClient(app) as client:
        r = client.post("/api/jobs/folder", json={
            "name": "x", "mode": "folder",
            "parent_dir": str(parent), "template_prompt": "p",
        })
        assert r.status_code == 400
