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


def test_pool_resizes_when_key_added(tmp_workspace: Path):
    """Adding/enabling a key via API should grow pool capacity without restart."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        initial_capacity = app.state.pool.concurrency
        # Add a real key → should grow pool
        r = client.post("/api/keys", json={"name": "k1", "key": "sk-test-aaaaaaaaaaaaaaaaaaaaaaaa"})
        assert r.status_code == 201
        # ensure_capacity grew the pool
        assert app.state.pool.concurrency >= initial_capacity
        # Add 2nd key
        client.post("/api/keys", json={"name": "k2", "key": "sk-test-bbbbbbbbbbbbbbbbbbbbbbbb"})
        # 2 enabled keys × per_key_concurrency
        assert app.state.pool.concurrency >= 2 * 5


def test_retry_all_failed(tmp_workspace: Path, sample_png: Path):
    """POST /api/jobs/{id}/retry-failed re-queues failed items."""
    import io
    import time
    from unittest.mock import AsyncMock

    from PIL import Image

    from app.core import openai_client
    from app.main import create_app

    buf = io.BytesIO()
    Image.new("RGB", (16, 16), (1, 2, 3)).save(buf, format="PNG")
    fake = openai_client.EditResult(image_bytes=buf.getvalue(), input_tokens=10, output_tokens=5)

    class FakeBadRequest(Exception):
        status_code = 400  # not retryable → fails permanently

    call_count = {"n": 0}

    async def fail_then_ok(*a, **kw):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            raise FakeBadRequest("bad")
        return fake

    app = create_app()
    with patch("app.core.executor.openai_client.edit_image_async",
               new=AsyncMock(side_effect=fail_then_ok)), TestClient(app) as client:
        r = client.post("/api/jobs", json={
            "name": "retry-all-test", "mode": "template",
            "template_prompt": "x", "ref_paths": [str(sample_png), str(sample_png)],
        })
        job_id = r.json()["id"]

        deadline = time.time() + 5
        while time.time() < deadline:
            d = client.get(f"/api/jobs/{job_id}").json()
            if d["status"] in ("done", "failed"):
                break
            time.sleep(0.1)
        assert d["status"] == "failed", d
        assert d["failed"] == 2

        # Now retry all → should succeed (call_count > 2 returns ok)
        r = client.post(f"/api/jobs/{job_id}/retry-failed")
        assert r.status_code == 200

        deadline = time.time() + 5
        while time.time() < deadline:
            d = client.get(f"/api/jobs/{job_id}").json()
            if d["status"] == "done":
                break
            time.sleep(0.1)
        assert d["status"] == "done"
        assert d["done"] == 2


def test_retry_all_failed_when_none(tmp_workspace: Path):
    from app.db.models import Job
    from app.db.session import SessionLocal, init_db
    from app.main import create_app

    init_db()
    db = SessionLocal()
    try:
        j = Job(name="empty", mode="template", status="done")
        db.add(j)
        db.commit()
        jid = j.id
    finally:
        db.close()

    app = create_app()
    with TestClient(app) as client:
        r = client.post(f"/api/jobs/{jid}/retry-failed")
        assert r.status_code == 409


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
