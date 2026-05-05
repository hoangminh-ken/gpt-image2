"""Mode A end-to-end test with mocked openai_client."""
from __future__ import annotations

import io
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image


def _png_bytes(color=(50, 200, 100)) -> bytes:
    img = Image.new("RGB", (64, 64), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_create_job_mode_a_runs_to_done(tmp_workspace: Path, sample_png: Path):
    from app.core import openai_client
    from app.db.session import init_db
    from app.main import create_app

    init_db()
    app = create_app()
    client = TestClient(app)

    fake_result = openai_client.EditResult(
        image_bytes=_png_bytes(),
        input_tokens=1000,
        output_tokens=500,
    )

    with patch("app.core.worker_sync.openai_client.edit_image", return_value=fake_result):
        resp = client.post(
            "/api/jobs",
            json={
                "name": "smoke",
                "mode": "template",
                "template_prompt": "a happy cat",
                "ref_paths": [str(sample_png)],
            },
        )
        assert resp.status_code == 201, resp.text
        job_id = resp.json()["id"]

        # poll until done
        deadline = time.time() + 5
        detail = None
        while time.time() < deadline:
            detail = client.get(f"/api/jobs/{job_id}").json()
            if detail["status"] in ("done", "failed"):
                break
            time.sleep(0.05)

    assert detail["status"] == "done", detail
    assert detail["total"] == 1
    assert detail["done"] == 1
    item = detail["items"][0]
    assert item["status"] == "done"
    assert item["input_tokens"] == 1000
    assert item["output_tokens"] == 500
    assert item["cost_usd"] > 0
    assert item["output_path"] is not None


def test_get_job_404(tmp_workspace: Path):
    from app.db.session import init_db
    from app.main import create_app

    init_db()
    app = create_app()
    client = TestClient(app)
    assert client.get("/api/jobs/9999").status_code == 404


def test_create_job_validation(tmp_workspace: Path):
    from app.db.session import init_db
    from app.main import create_app

    init_db()
    app = create_app()
    client = TestClient(app)
    resp = client.post(
        "/api/jobs",
        json={"name": "x", "mode": "template", "template_prompt": "p", "ref_paths": []},
    )
    assert resp.status_code == 422
