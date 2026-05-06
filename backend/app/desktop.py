"""Desktop entry point.

Run as packaged .exe (PyInstaller --windowed): launches a native window via
pywebview pointing at an embedded uvicorn server. Falls back to default browser
if pywebview unavailable. First-run bootstraps a writable .env from template.
"""
from __future__ import annotations

import os
import sys

# CRITICAL: in PyInstaller --windowed mode (--noconsole), sys.stdout/stderr
# are None. uvicorn's default log formatter calls .isatty() on them and
# raises AttributeError during Config(...) init. Patch BEFORE any other import
# touches stdio (logging, uvicorn, etc.).
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import logging  # noqa: E402
import logging.handlers  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import urllib.request  # noqa: E402
import webbrowser  # noqa: E402

from app.paths import env_example_template, env_file_path, is_frozen, user_data_root  # noqa: E402

logger = logging.getLogger("gpt_image2.desktop")

WINDOW_TITLE = "gpt-image2 — Batch Image Generator"
DEFAULT_PORT = 8767


def _setup_logging() -> None:
    """File-based logging in frozen mode (no console to print to)."""
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handlers: list[logging.Handler] = []
    if is_frozen():
        log_dir = user_data_root() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(fmt))
        handlers.append(fh)
    else:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(fmt))
        handlers.append(sh)
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)


def _ensure_env() -> bool:
    """Create .env from template if missing. Returns True if fresh template was written."""
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
    """Start uvicorn in a daemon thread.

    log_config=None disables uvicorn's dictConfig (avoids ColourizedFormatter +
    isatty() crash in windowed mode). Our own logging already covers events.
    """
    import uvicorn

    from app.main import app

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_config=None,         # use our logging, not uvicorn's
        log_level="warning",
        access_log=False,
        lifespan="on",
    )
    server = uvicorn.Server(config)

    def run():
        try:
            server.run()
        except Exception as exc:  # noqa: BLE001
            logger.exception("uvicorn server thread crashed: %s", exc)

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
        # Block forever (server runs in daemon thread; user closes via Task Manager
        # or by opening browser and not closing this process — exposed as fallback only).
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            pass
        return

    webview.create_window(WINDOW_TITLE, url, width=1280, height=820, resizable=True)
    webview.start()  # blocks until window closed


def main() -> int:
    _setup_logging()

    fresh = _ensure_env()
    logger.info("Data directory: %s", user_data_root())
    if fresh:
        logger.info("Created fresh .env at %s; paste your OPENAI_API_KEY there.", env_file_path())

    port = _find_port()
    url = f"http://127.0.0.1:{port}/"
    logger.info("Starting server on %s", url)
    _run_server(port)

    if not _wait_for_health(url):
        logger.error("Server did not become healthy in 30s. Aborting.")
        return 1

    logger.info("Server ready, launching window")
    _open_window(url)
    logger.info("Window closed, exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
