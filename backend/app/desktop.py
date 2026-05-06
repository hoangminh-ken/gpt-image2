"""Desktop entry point.

Run as packaged .exe (PyInstaller): launches a native window via pywebview
pointing at an embedded uvicorn server. Falls back to default browser if
pywebview unavailable. First-run bootstraps a writable .env from template.
"""
from __future__ import annotations

import logging
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

from app.paths import env_example_template, env_file_path, user_data_root

logger = logging.getLogger("gpt_image2.desktop")

WINDOW_TITLE = "gpt-image2 — Batch Image Generator"
DEFAULT_PORT = 8767


def _ensure_env() -> bool:
    """Create .env from template if missing. Returns True if a fresh template was written."""
    p = env_file_path()
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(env_example_template(), encoding="utf-8")
    return True


def _find_port(prefer: int = DEFAULT_PORT) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", prefer))
            return prefer
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _wait_for_health(url: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
    return False


def _run_server(port: int) -> threading.Thread:
    """Start uvicorn in a daemon thread."""
    import uvicorn

    from app.main import app

    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning",
        access_log=False, lifespan="on",
    )
    server = uvicorn.Server(config)

    def run():
        server.run()

    t = threading.Thread(target=run, daemon=True, name="uvicorn-thread")
    t.start()
    return t


def _open_window(url: str) -> None:
    """Try pywebview native window; fall back to default browser."""
    try:
        import webview
    except Exception as exc:  # noqa: BLE001
        logger.warning("pywebview unavailable (%s); opening browser", exc)
        webbrowser.open(url)
        # Block on stdin so the console window stays open
        try:
            print(f"\nServer running at {url}\nPress Ctrl+C to quit.\n")
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        return

    webview.create_window(WINDOW_TITLE, url, width=1280, height=820, resizable=True)
    webview.start()  # blocks until window closed


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    fresh = _ensure_env()
    data_dir = user_data_root()
    logger.info("Data directory: %s", data_dir)
    if fresh:
        logger.info("Created fresh .env at %s — paste your OPENAI_API_KEY there.", env_file_path())

    port = _find_port()
    url = f"http://127.0.0.1:{port}/"
    _run_server(port)

    if not _wait_for_health(url):
        logger.error("Server did not become healthy in 30s. Aborting.")
        return 1

    logger.info("Ready: %s", url)
    _open_window(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
