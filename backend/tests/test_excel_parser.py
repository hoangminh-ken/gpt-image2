"""Excel parser unit tests."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import openpyxl

from app.parsers.excel import parse_excel


def _make_xlsx(rows: list[list[object]]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_valid_rows(sample_png: Path):
    refs = str(sample_png)
    data = _make_xlsx([
        ["prompt", "refs", "output_name"],
        ["a happy cat", refs, "cat_01.png"],
        ["wide landscape", f"{refs}|{refs}", "scene.png"],
    ])
    result = parse_excel(data)
    assert result.summary == {"total": 2, "valid": 2, "invalid": 0}
    assert len(result.rows) == 2
    assert result.rows[1].refs == [str(sample_png).replace("\\", "/")] * 2
    assert result.rows[0].output_name == "cat_01.png"


def test_missing_columns():
    data = _make_xlsx([["foo", "bar"], ["x", "y"]])
    result = parse_excel(data)
    assert result.summary["error"].startswith("missing required")


def test_invalid_paths(sample_png: Path):
    data = _make_xlsx([
        ["prompt", "refs"],
        ["good", str(sample_png)],
        ["bad path", "C:/no/such/file.png"],
        ["", str(sample_png)],
    ])
    result = parse_excel(data)
    assert result.summary["total"] == 3
    assert result.summary["valid"] == 1
    assert result.rows[1].valid is False
    assert any("not found" in e for e in result.rows[1].errors)
    assert result.rows[2].valid is False


def test_skips_blank_rows(sample_png: Path):
    data = _make_xlsx([
        ["prompt", "refs"],
        ["a", str(sample_png)],
        [None, None],
        ["b", str(sample_png)],
    ])
    result = parse_excel(data)
    assert result.summary["total"] == 2  # blank skipped


def test_invalid_output_name(sample_png: Path):
    data = _make_xlsx([
        ["prompt", "refs", "output_name"],
        ["x", str(sample_png), "../escape.png"],
    ])
    result = parse_excel(data)
    assert result.rows[0].valid is False
    assert any("output_name" in e for e in result.rows[0].errors)


def test_too_many_refs(sample_png: Path):
    refs = "|".join([str(sample_png)] * 10)
    data = _make_xlsx([
        ["prompt", "refs"],
        ["x", refs],
    ])
    result = parse_excel(data)
    assert result.rows[0].valid is False
    assert any("too many refs" in e for e in result.rows[0].errors)
