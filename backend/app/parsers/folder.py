"""Mode C parser: walk a parent folder, collect images per subfolder."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_SUBFOLDERS = 200
MAX_IMAGES_PER_SUBFOLDER = 100
MAX_TOTAL_IMAGES = 1000


@dataclass
class SubfolderEntry:
    name: str
    path: str
    images: list[str]
    skipped_existing: int  # how many would be skipped because output exists


@dataclass
class FolderScanResult:
    parent_dir: str
    subfolders: list[SubfolderEntry]
    total_images: int
    total_to_run: int  # excluding skipped
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "parent_dir": self.parent_dir,
            "subfolders": [asdict(s) for s in self.subfolders],
            "total_images": self.total_images,
            "total_to_run": self.total_to_run,
            "error": self.error,
        }


def scan_parent(
    parent_dir: str,
    output_subfolder: str = "generated",
    skip_existing: bool = True,
) -> FolderScanResult:
    """One level deep: each immediate subdir of parent contributes images.

    For each image, the prospective output path is
    `<subfolder>/<output_subfolder>/<image_stem>.png`. When skip_existing=True,
    files that already exist there are excluded from the run count.
    """
    p = Path(parent_dir).expanduser()
    if not p.exists():
        return FolderScanResult(parent_dir=str(p), subfolders=[], total_images=0,
                                total_to_run=0, error=f"Path does not exist: {p}")
    if not p.is_dir():
        return FolderScanResult(parent_dir=str(p), subfolders=[], total_images=0,
                                total_to_run=0, error=f"Not a directory: {p}")

    sub_entries: list[SubfolderEntry] = []
    total_images = 0
    total_to_run = 0

    subdirs = sorted([c for c in p.iterdir() if c.is_dir()])[:MAX_SUBFOLDERS]
    for sub in subdirs:
        # Skip the output subfolder itself if it appears (avoid recursion when re-running)
        if sub.name == output_subfolder:
            continue
        out_dir = sub / output_subfolder
        images: list[str] = []
        skipped = 0
        for f in sorted(sub.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() not in IMAGE_EXTS:
                continue
            if skip_existing and (out_dir / f"{f.stem}.png").is_file():
                skipped += 1
                continue
            images.append(str(f.resolve()))
            if len(images) >= MAX_IMAGES_PER_SUBFOLDER:
                break
        if not images and skipped == 0:
            continue
        sub_entries.append(SubfolderEntry(
            name=sub.name,
            path=str(sub.resolve()),
            images=images,
            skipped_existing=skipped,
        ))
        total_images += len(images) + skipped
        total_to_run += len(images)
        if total_to_run >= MAX_TOTAL_IMAGES:
            break

    return FolderScanResult(
        parent_dir=str(p.resolve()),
        subfolders=sub_entries,
        total_images=total_images,
        total_to_run=total_to_run,
    )
