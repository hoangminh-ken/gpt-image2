"""System endpoints (open-folder) tests."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_open_folder_validates_path(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        # Path outside allowed roots → 403
        resp = client.post(
            "/api/system/open-folder",
            json={"path": "C:/Windows/System32"},
        )
        assert resp.status_code in (403, 404)


def test_open_folder_under_output_dir(tmp_workspace: Path):
    from app.config import settings as cfg
    from app.main import create_app

    out = cfg.output_path / "test-job"
    out.mkdir(parents=True, exist_ok=True)

    app = create_app()
    with patch("app.api.system._open") as mock_open, TestClient(app) as client:
        resp = client.post(
            "/api/system/open-folder",
            json={"path": str(out)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        mock_open.assert_called_once()


def test_open_folder_traversal_rejected(tmp_workspace: Path):
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        # Path tries to escape via .. (resolves outside allowed roots)
        resp = client.post(
            "/api/system/open-folder",
            json={"path": "outputs/../../../../etc/passwd"},
        )
        assert resp.status_code in (403, 404)
