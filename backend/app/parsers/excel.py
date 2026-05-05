"""Mode B parser: read .xlsx with columns prompt | refs | output_name (optional)."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path

import openpyxl

MAX_ROWS = 1000
MAX_REFS_PER_ROW = 8
MAX_PROMPT_LEN = 32000  # gpt-image-2 input is token-bound, not char-bound; this is a sanity cap
ALLOWED_REF_EXT = {".png", ".jpg", ".jpeg", ".webp"}
NAME_RE = re.compile(r"^[\w\-. ]{1,200}$", re.UNICODE)


@dataclass
class RowDiagnostic:
    row_idx: int  # 1-based row number in Excel (excluding header)
    prompt: str
    refs: list[str]
    output_name: str | None
    valid: bool
    errors: list[str]


@dataclass
class ParseResult:
    headers: list[str]
    rows: list[RowDiagnostic]
    summary: dict

    def to_dict(self) -> dict:
        return {
            "headers": self.headers,
            "rows": [asdict(r) for r in self.rows],
            "summary": self.summary,
        }


def _normalize_ref(p: str) -> str:
    return p.strip().replace("\\", "/")


def _validate_row(prompt: str, refs: list[str], output_name: str | None) -> list[str]:
    errors: list[str] = []
    if not prompt or not prompt.strip():
        errors.append("prompt is empty")
    elif len(prompt) > MAX_PROMPT_LEN:
        errors.append(f"prompt exceeds {MAX_PROMPT_LEN} chars")
    if not refs:
        errors.append("refs is empty")
    elif len(refs) > MAX_REFS_PER_ROW:
        errors.append(f"too many refs ({len(refs)} > {MAX_REFS_PER_ROW})")
    for r in refs:
        path = Path(r)
        if ".." in path.parts:
            errors.append(f"ref contains '..': {r}")
            continue
        if path.suffix.lower() not in ALLOWED_REF_EXT:
            errors.append(f"ref has bad extension: {path.name}")
            continue
        if not path.is_file():
            errors.append(f"ref not found: {r}")
    if (output_name is not None and output_name != "") and (
        not NAME_RE.match(output_name) or "/" in output_name or "\\" in output_name
    ):
        errors.append(f"invalid output_name: {output_name!r}")
    return errors


def parse_excel(buf: bytes) -> ParseResult:
    wb = openpyxl.load_workbook(BytesIO(buf), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return ParseResult([], [], {"total": 0, "valid": 0, "invalid": 0, "error": "no active sheet"})

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        return ParseResult([], [], {"total": 0, "valid": 0, "invalid": 0, "error": "empty sheet"})

    headers_raw = [(c.strip().lower() if isinstance(c, str) else "") for c in header_row]
    col_idx = {h: i for i, h in enumerate(headers_raw) if h}

    if "prompt" not in col_idx or "refs" not in col_idx:
        return ParseResult(
            headers=list(headers_raw),
            rows=[],
            summary={"total": 0, "valid": 0, "invalid": 0,
                     "error": "missing required columns: prompt, refs"},
        )

    rows: list[RowDiagnostic] = []
    for n, row in enumerate(rows_iter, start=1):
        if n > MAX_ROWS:
            break
        if not row or all(c is None or (isinstance(c, str) and not c.strip()) for c in row):
            continue  # skip blank lines
        prompt = str(row[col_idx["prompt"]] or "").strip()
        refs_raw = str(row[col_idx["refs"]] or "").strip()
        refs = [_normalize_ref(p) for p in refs_raw.split("|") if p.strip()] if refs_raw else []
        output_name = None
        if "output_name" in col_idx:
            v = row[col_idx["output_name"]]
            output_name = str(v).strip() if v is not None and str(v).strip() else None

        errors = _validate_row(prompt, refs, output_name)
        rows.append(RowDiagnostic(
            row_idx=n, prompt=prompt, refs=refs, output_name=output_name,
            valid=not errors, errors=errors,
        ))

    valid = sum(1 for r in rows if r.valid)
    return ParseResult(
        headers=list(headers_raw),
        rows=rows,
        summary={"total": len(rows), "valid": valid, "invalid": len(rows) - valid},
    )


def build_items_from_rows(rows: list[dict]) -> list[dict]:
    """Convert parsed/sanitized rows (from API payload) into ItemSpec-compatible dicts."""
    out = []
    for i, r in enumerate(rows):
        prompt = r.get("prompt", "").strip()
        refs = [str(p).strip() for p in r.get("refs", []) if str(p).strip()]
        if not prompt or not refs:
            continue
        out.append({
            "row_idx": i,
            "prompt": prompt,
            "refs": refs,
            "output_name": r.get("output_name") or None,
        })
    return out
