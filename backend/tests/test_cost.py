"""Cost summary + reconcile endpoint tests."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import respx
from fastapi.testclient import TestClient
from httpx import Response


def _seed_costs(rows: list[tuple[str, str, int, int, str]]):
    from app.db.models import CostDaily
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        for d, source, in_t, out_t, cost in rows:
            db.add(CostDaily(date=d, source=source, input_tokens=in_t,
                             output_tokens=out_t, cost_usd=Decimal(cost)))
        db.commit()
    finally:
        db.close()


def test_cost_summary_empty(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/cost")
        assert resp.status_code == 200
        body = resp.json()
        assert body["today"]["local_usd"] == 0
        assert body["admin_key_configured"] is False


def test_cost_summary_with_data(tmp_workspace: Path):
    from app.db.session import init_db
    from app.main import create_app

    init_db()
    today = date.today().isoformat()
    _seed_costs([
        (today, "local", 1000, 500, "0.020000"),
        (today, "openai", 1000, 500, "0.020500"),
    ])
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/api/cost")
        body = resp.json()
        assert body["today"]["local_usd"] == 0.02
        assert body["today"]["openai_usd"] == 0.0205
        # drift = |0.0205 - 0.02| / 0.02 * 100 = 2.5%
        assert abs((body["today"]["drift_pct"] or 0) - 2.5) < 0.1


def test_reconcile_no_admin_key(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        resp = client.post("/api/cost/reconcile")
        assert resp.status_code == 400
        assert "OPENAI_ADMIN_KEY" in resp.json()["detail"]


def test_reconcile_success(tmp_workspace: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_ADMIN_KEY", "sk-admin-test")
    # Force re-import of settings + dependent modules
    import sys
    for mod in list(sys.modules.keys()):
        if mod.startswith("app."):
            del sys.modules[mod]
    from app.main import create_app

    today_unix = int(datetime.now(tz=timezone.utc).timestamp())
    sample_payload = {
        "data": [
            {
                "start_time": today_unix - 3600,
                "results": [{"input_tokens": 5000, "output_tokens": 2000,
                             "num_model_requests": 3}],
            }
        ],
        "next_page": None,
    }

    app = create_app()
    with respx.mock(assert_all_called=False) as router, TestClient(app) as client:
        router.get("https://api.openai.com/v1/organization/usage/images").mock(
            return_value=Response(200, json=sample_payload)
        )
        resp = client.post("/api/cost/reconcile")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["count"] == 1
        # cost should be (5000*8 + 2000*30) / 1M = 0.04 + 0.06 = 0.10
        from app.db.models import CostDaily
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            rows = db.query(CostDaily).filter(CostDaily.source == "openai").all()
            assert len(rows) == 1
            assert abs(float(rows[0].cost_usd) - 0.10) < 0.001
        finally:
            db.close()
    _ = patch  # silence unused
