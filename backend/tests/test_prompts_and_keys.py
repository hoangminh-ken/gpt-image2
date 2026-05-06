"""Prompt library + multi-API-key tests."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_prompt_crud(tmp_workspace: Path):
    from app.main import create_app
    app = create_app()
    with TestClient(app) as client:
        # List empty
        assert client.get("/api/prompts").json() == []

        # Create
        r = client.post("/api/prompts", json={"name": "concrete-bg", "content": "Replace bg with concrete"})
        assert r.status_code == 201
        pid = r.json()["id"]
        assert r.json()["name"] == "concrete-bg"

        # Duplicate name → 409
        r2 = client.post("/api/prompts", json={"name": "concrete-bg", "content": "x"})
        assert r2.status_code == 409

        # Update
        r = client.put(f"/api/prompts/{pid}", json={"name": "concrete-v2", "content": "updated"})
        assert r.status_code == 200
        assert r.json()["name"] == "concrete-v2"

        # Increment use
        r = client.post(f"/api/prompts/{pid}/use")
        assert r.json()["used_count"] == 1

        # List ordered by use_count desc
        items = client.get("/api/prompts").json()
        assert len(items) == 1

        # Delete
        assert client.delete(f"/api/prompts/{pid}").status_code == 204
        assert client.get("/api/prompts").json() == []


def test_keys_crud_and_mask(tmp_workspace: Path):
    from app.main import create_app
    app = create_app()
    with TestClient(app) as client:
        # Create
        r = client.post("/api/keys", json={"name": "Acct A", "key": "sk-test-aaaaaaaaaaaaaaaaaaaaaaaa"})
        assert r.status_code == 201
        body = r.json()
        kid = body["id"]
        # Masked, never returns plaintext key
        assert "key_masked" in body
        assert "sk-test" in body["key_masked"]
        assert "aaaaaaaaaaaaaaaa" not in body["key_masked"]
        assert "key" not in body  # raw key never exposed

        # Toggle
        r = client.put(f"/api/keys/{kid}", json={"enabled": False})
        assert r.json()["enabled"] is False

        # Delete
        assert client.delete(f"/api/keys/{kid}").status_code == 204


def test_key_manager_round_robin(tmp_workspace: Path):
    from app.core.key_manager import key_manager
    from app.db.models import ApiKey
    from app.db.session import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        for i, k in enumerate(["sk-key-A", "sk-key-B", "sk-key-C"]):
            db.add(ApiKey(name=f"k{i}", key=k, enabled=True))
        db.commit()
    finally:
        db.close()

    # 6 calls should cycle A,B,C,A,B,C
    seen = []
    for _ in range(6):
        _, key = key_manager.next()
        seen.append(key)
    assert seen == ["sk-key-A", "sk-key-B", "sk-key-C"] * 2


def test_key_manager_falls_back_to_env(tmp_workspace: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-fallback")
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]

    from app.core.key_manager import key_manager
    from app.db.session import init_db

    init_db()  # tables exist but api_keys is empty → fallback path
    key_id, key = key_manager.next()
    assert key_id is None  # fallback to env
    assert key == "sk-env-fallback"


def test_key_manager_skips_rate_limited(tmp_workspace: Path):
    from datetime import datetime, timedelta

    from app.core.key_manager import key_manager
    from app.db.models import ApiKey
    from app.db.session import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        db.add(ApiKey(name="hot", key="sk-hot", enabled=True,
                      rate_limited_until=datetime.utcnow() + timedelta(minutes=5)))
        db.add(ApiKey(name="cool", key="sk-cool", enabled=True))
        db.commit()
    finally:
        db.close()

    for _ in range(3):
        _, k = key_manager.next()
        assert k == "sk-cool"  # hot key skipped


def test_executor_uses_key_manager(tmp_workspace: Path, sample_png: Path):
    """End-to-end: job runs, executor pulls key from manager, mark_used called."""
    import io
    from unittest.mock import AsyncMock

    from PIL import Image

    from app.core import openai_client
    from app.db.models import ApiKey
    from app.db.session import SessionLocal, init_db
    from app.main import create_app

    init_db()
    db = SessionLocal()
    try:
        db.add(ApiKey(name="primary", key="sk-from-table", enabled=True))
        db.commit()
    finally:
        db.close()

    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(buf, format="PNG")
    fake = openai_client.EditResult(image_bytes=buf.getvalue(), input_tokens=10, output_tokens=5)

    captured_keys: list[str | None] = []

    async def fake_edit(prompt, ref_paths, size=None, quality=None, api_key=None):
        captured_keys.append(api_key)
        return fake

    app = create_app()
    with patch("app.core.executor.openai_client.edit_image_async", new=AsyncMock(side_effect=fake_edit)), TestClient(app) as client:
        r = client.post("/api/jobs", json={
            "name": "key-dispatch", "mode": "template",
            "template_prompt": "x", "ref_paths": [str(sample_png)],
        })
        assert r.status_code == 201
        # poll
        import time
        deadline = time.time() + 5
        while time.time() < deadline:
            d = client.get(f"/api/jobs/{r.json()['id']}").json()
            if d["status"] in ("done", "failed"):
                break
            time.sleep(0.1)
        assert d["status"] == "done"

    assert captured_keys == ["sk-from-table"]
