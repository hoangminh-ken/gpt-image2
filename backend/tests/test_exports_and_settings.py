"""ZIP export + settings endpoint tests."""
from __future__ import annotations

import io
import zipfile
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient


def _make_done_item(workspace: Path, png_bytes: bytes) -> tuple[int, int, str]:
    """Create a Job with one completed item; returns (job_id, item_id, output_path_rel)."""
    from app.config import settings as cfg
    from app.db.models import Job, JobItem
    from app.db.session import SessionLocal
    out_dir = cfg.output_path / "1"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "0000-test.png"
    out_file.write_bytes(png_bytes)
    from app.utils.slug import store_path
    rel = store_path(out_file, cfg.project_root)

    db = SessionLocal()
    try:
        job = Job(name="export-test", mode="template", status="done")
        db.add(job)
        db.flush()
        item = JobItem(
            job_id=job.id, row_idx=0, prompt="hi", refs_json=["x.png"],
            status="done", output_path=rel, input_tokens=10, output_tokens=5,
            cost_usd=Decimal("0.000220"),
        )
        db.add(item)
        db.commit()
        return job.id, item.id, rel
    finally:
        db.close()


def test_export_zip_contains_manifest_and_image(tmp_workspace: Path):
    from PIL import Image

    from app.db.session import init_db
    from app.main import create_app

    init_db()
    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(buf, format="PNG")
    job_id, _, _ = _make_done_item(tmp_workspace, buf.getvalue())

    app = create_app()
    with TestClient(app) as client:
        resp = client.get(f"/api/jobs/{job_id}/export.zip")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        names = z.namelist()
        assert "manifest.json" in names
        assert any(n.endswith(".png") for n in names)
        import json
        manifest = json.loads(z.read("manifest.json"))
        assert manifest["job_id"] == job_id
        assert len(manifest["items"]) == 1


def test_export_zip_no_items(tmp_workspace: Path):
    from app.db.models import Job
    from app.db.session import SessionLocal, init_db
    from app.main import create_app

    init_db()
    db = SessionLocal()
    try:
        job = Job(name="empty", mode="template", status="pending")
        db.add(job)
        db.commit()
        jid = job.id
    finally:
        db.close()

    app = create_app()
    with TestClient(app) as client:
        resp = client.get(f"/api/jobs/{jid}/export.zip")
        assert resp.status_code == 404


def test_settings_update_writes_env_and_mutates_live(tmp_workspace: Path, monkeypatch):
    # Point env file to tmpdir via env var (honored by app.paths.env_file_path)
    fake_env = tmp_workspace / ".env"
    monkeypatch.setenv("GPT_IMAGE2_ENV_FILE", str(fake_env))

    from app.main import create_app
    app = create_app()

    with TestClient(app) as client:
        # PUT a key
        resp = client.put("/api/settings", json={"openai_api_key": "sk-newkey-12345678901234567890"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["openai_api_key_set"] is True
        # Persisted to .env
        assert fake_env.read_text(encoding="utf-8").splitlines().__contains__(
            "OPENAI_API_KEY=sk-newkey-12345678901234567890"
        )
        # Live: GET reflects new key
        get = client.get("/api/settings").json()
        assert get["openai_api_key_set"] is True
        # Update model + concurrency at once
        resp = client.put("/api/settings", json={
            "openai_image_model": "gpt-image-1-mini",
            "default_concurrency": 3,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["openai_image_model"] == "gpt-image-1-mini"
        # Concurrency is RESTART_FIELDS — should be flagged
        assert "default_concurrency" in body.get("restart_required_for", [])
        # Empty string clears
        resp = client.put("/api/settings", json={"openai_admin_key": ""})
        assert resp.status_code == 200
        assert resp.json()["openai_admin_key_set"] is False
        # Validation: out-of-range concurrency rejected
        resp = client.put("/api/settings", json={"default_concurrency": 999})
        assert resp.status_code == 422


def test_settings_masks_keys(tmp_workspace: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-1234567890abcdef1234567890abcdef")
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        body = resp.json()
        assert body["openai_api_key_set"] is True
        assert "sk-test" in body["openai_api_key_masked"]
        assert "1234567890abcdef" not in body["openai_api_key_masked"]
