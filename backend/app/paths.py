"""Path resolution for dev vs frozen (PyInstaller) mode.

Dev:        data/, outputs/, backend/.env  → project_root
Frozen:     data/, outputs/, .env          → user_data_root (APPDATA / Application Support / XDG_DATA_HOME)
            frontend/dist/                 → bundled inside .exe (sys._MEIPASS)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "gpt-image2"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_root() -> Path:
    """Where bundled read-only resources live (frontend/dist when frozen, project root in dev)."""
    if is_frozen():
        # PyInstaller --onefile extracts to _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parents[2]


def user_data_root() -> Path:
    """Writable user-specific data directory (cross-platform)."""
    if is_frozen():
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        d = base / APP_NAME
    else:
        # Dev: store alongside source for convenience
        d = Path(__file__).resolve().parents[2]
    d.mkdir(parents=True, exist_ok=True)
    return d


def env_file_path() -> Path:
    """Where .env lives. In frozen mode, in user_data_root; in dev, backend/.env."""
    if is_frozen():
        return user_data_root() / ".env"
    return Path(__file__).resolve().parents[1] / ".env"


def env_example_template() -> str:
    """Default .env contents written on first run when no .env exists."""
    return (
        "# OpenAI API key (REQUIRED). Get from https://platform.openai.com/api-keys\n"
        "OPENAI_API_KEY=\n\n"
        "# Optional: org admin key for cost reconcile (Cost page → Sync OpenAI Usage)\n"
        "OPENAI_ADMIN_KEY=\n\n"
        "# Image model. Default = alias to latest gpt-image-2.\n"
        "OPENAI_IMAGE_MODEL=gpt-image-2\n\n"
        "# Concurrency for parallel API calls\n"
        "DEFAULT_CONCURRENCY=5\n\n"
        "# Auto-resize ref images larger than this (longest side, px)\n"
        "MAX_REF_DIMENSION=2048\n"
    )
