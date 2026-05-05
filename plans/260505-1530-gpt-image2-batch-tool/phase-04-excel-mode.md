---
phase: 4
title: "Mode B Excel Parser"
status: completed
priority: P2
effort: "0.5d"
dependencies: [3]
completed: 2026-05-05
smoke_test: "PASS — 6 parser tests, valid/invalid/multi-ref/blank/output_name/too-many-refs scenarios. Backend 37/37 tests, frontend build 342KB."
---

# Phase 4: Mode B Excel Parser

## Overview
Add Excel-driven batch input (Mode B): upload .xlsx → parse rows of `prompt | refs (pipe-delimited) | output_name (optional)` → preview validation → create job.

## Context Links
- [plan.md](./plan.md)
- [brainstorm-summary.md](./brainstorm-summary.md) §4 (Mode B)

## Requirements

### Functional
- `POST /api/jobs/parse-excel` — multipart upload, returns parsed rows + validation results
- `POST /api/jobs` accepts `mode="excel"` payload: `{name, rows: [{prompt, refs[], output_name?}], output_dir?}`
- Validation per row:
  - prompt non-empty
  - each ref path exists on disk and is image (png/jpg/webp)
  - output_name (if provided) sanitized — no `/`, `\`, `..`
- UI: NewJob page gets second tab "Excel Mode"; user uploads file → table preview with green/red row icons → submit only if all rows valid (or override "skip invalid" checkbox)

### Non-Functional
- Use `openpyxl` (read-only)
- Max file size 10MB, max 1000 rows (configurable)
- Validation runs server-side; client just renders results

## Architecture

```
backend/app/parsers/excel.py
  parse_excel(file_bytes) -> ParseResult
    - openpyxl read-only iterator
    - detect headers: prompt, refs, output_name (case-insensitive, trimmed)
    - split refs on '|', strip whitespace
    - return rows + per-row validation diagnostics

backend/app/api/jobs.py (modify)
  POST /api/jobs/parse-excel — preview only, no DB write
  POST /api/jobs — accept mode='excel' with already-parsed rows

frontend/src/pages/NewJob.tsx (modify)
  <Tabs> Mode A | Excel Mode
  <ExcelUpload> drop zone → POST parse-excel → render table

frontend/src/components/ExcelPreviewTable.tsx
  - row index, prompt (truncated), refs count + first thumb, output_name, validation badge
  - bottom summary: X valid / Y invalid / total
  - "Skip invalid" toggle, "Create job" button
```

## Related Code Files

### Create
- `backend/app/parsers/excel.py`
- `backend/tests/test_excel_parser.py`
- `backend/tests/fixtures/sample_valid.xlsx`
- `backend/tests/fixtures/sample_invalid_paths.xlsx`
- `frontend/src/components/ExcelUpload.tsx`
- `frontend/src/components/ExcelPreviewTable.tsx`

### Modify
- `backend/app/api/jobs.py` — add `parse-excel` endpoint, extend `create job` for `mode='excel'`
- `backend/app/parsers/template.py` (rename to `__init__.py` package or add `excel.py` sibling)
- `frontend/src/pages/NewJob.tsx` — add Tabs, integrate ExcelUpload
- `frontend/src/api/jobs.ts` — `parseExcel(file)`, `createExcelJob(rows)`
- `README.md` — add Excel format spec section

## Implementation Steps

1. `parsers/excel.py`:
   ```python
   def parse_excel(buf: bytes, allowed_ref_dirs: list[Path]) -> ParseResult:
       wb = openpyxl.load_workbook(BytesIO(buf), read_only=True, data_only=True)
       ws = wb.active
       headers = {cell.value.lower().strip(): idx for idx, cell in enumerate(next(ws.iter_rows(max_row=1)))}
       require: 'prompt', 'refs'; optional: 'output_name'
       for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=1):
           prompt = row[headers['prompt']]
           refs = [r.strip() for r in (row[headers['refs']] or '').split('|') if r.strip()]
           output_name = row[headers.get('output_name', -1)] if 'output_name' in headers else None
           validate(prompt, refs, output_name) -> diagnostics
   ```
2. Validation rules:
   - prompt: non-empty, ≤4000 chars
   - refs: ≥1, ≤8 paths, each `Path(p).exists() and suffix in {.png, .jpg, .jpeg, .webp}`
   - output_name: regex `^[\w\-\. ]+$`, no `..`, length ≤100
3. `api/jobs.py` `parse-excel` endpoint:
   - accept multipart `file: UploadFile`, max 10MB
   - return `{headers_detected, rows: [...], summary: {total, valid, invalid}}`
4. Extend `POST /api/jobs` with `mode='excel'` payload — items inserted from validated rows; skip rows marked `skip=true` or `valid=false` (if not skip-invalid mode, return 400)
5. `ExcelUpload.tsx`: drop zone → upload → render preview
6. `ExcelPreviewTable.tsx`: virtualized only if >100 rows (defer); show diagnostics on hover
7. NewJob Tab integration; "Create" button calls `createJob({mode:'excel', rows})`
8. Tests:
   - parser: valid sample, missing column, invalid paths, multi-ref split, empty rows
   - integration: upload via TestClient, assert response shape

## Todo List
- [ ] excel.py parser with header detection
- [ ] Validation rules + diagnostics structure
- [ ] /api/jobs/parse-excel endpoint
- [ ] Extend POST /api/jobs for mode='excel'
- [ ] Sample fixtures (valid + invalid)
- [ ] Parser unit tests
- [ ] ExcelUpload component
- [ ] ExcelPreviewTable component
- [ ] NewJob Tabs integration
- [ ] README format spec section
- [ ] End-to-end smoke: upload xlsx → see table → create → run

## Success Criteria
- [ ] Upload valid 50-row xlsx → all rows green → create job → all 50 items processed
- [ ] Upload xlsx with 5 invalid rows → red badges visible, "Skip invalid" checkbox lets user proceed with 45 valid
- [ ] Multi-ref row (3 paths via `|`) generates 1 image with 3 inputs (verify via item.refs_json length=3)
- [ ] Excel parser tests pass

## Risk Assessment
- **Risk**: Path on Excel uses backslash on Windows but forward slash on macOS → **Mitigation**: normalize via `Path()`, accept both
- **Risk**: Relative paths break depending on CWD → **Mitigation**: resolve relative to Excel file's directory if metadata available, else require absolute
- **Risk**: Massive xlsx hangs server → **Mitigation**: enforce row count + file size limits before parsing
- **Risk**: Header naming variation (Prompt vs prompt vs PROMPT) → **Mitigation**: lowercase + strip in detection

## Security Considerations
- Reject `..` in any path component
- Limit allowed_ref_dirs (configurable in Settings) — prevents reading arbitrary disk paths
- File upload size cap enforced before reading

## Next Steps
Phase 5 adds OpenAI Usage API reconcile to dashboard.
