"""Slugify helpers for output filenames."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def store_path(p: Path, base: Path) -> str:
    """Return path as string relative to `base` if possible, else absolute (POSIX-style)."""
    p = p.resolve()
    base = base.resolve()
    try:
        rel = p.relative_to(base)
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def slugify(text: str, max_len: int = 40) -> str:
    """Convert prompt/text to a safe filename slug. Lowercase, ASCII-only, hyphens."""
    if not text:
        return "untitled"
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    text = re.sub(r"[\s-]+", "-", text)
    text = text.strip("-")
    return (text[:max_len] or "untitled").rstrip("-")


def safe_filename(name: str) -> str:
    """Validate user-provided output filename. Reject any path separator."""
    if not name or "/" in name or "\\" in name:
        return ""
    if ".." in name or name.startswith("."):
        return ""
    if not re.match(r"^[\w\-. ]{1,200}$", name, re.UNICODE):
        return ""
    return name
