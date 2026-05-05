#!/usr/bin/env bash
# ============================================================================
# gpt-image2 — Unix one-click launcher (macOS/Linux)
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8767}"
VENV="backend/.venv"
DIST="frontend/dist"

# --- Pre-flight checks -------------------------------------------------------
command -v python3 >/dev/null 2>&1 || { echo "[ERROR] python3 not found. Install Python 3.10+"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "[ERROR] node not found. Install Node.js 20+"; exit 1; }

if [[ ! -f backend/.env ]]; then
    echo "[SETUP] backend/.env not found. Creating from .env.example..."
    cp backend/.env.example backend/.env
    echo
    echo "[ACTION REQUIRED] Edit backend/.env and paste your OpenAI API key:"
    echo "    OPENAI_API_KEY=sk-..."
    echo
    echo "Then re-run ./start.sh"
    exit 0
fi

# --- Bootstrap Python venv ---------------------------------------------------
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "[SETUP] Creating Python virtual environment..."
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --upgrade pip
    "$VENV/bin/python" -m pip install -r backend/requirements.txt
fi

# --- Build frontend if needed ------------------------------------------------
if [[ ! -f "$DIST/index.html" ]]; then
    echo "[SETUP] Building frontend (first run, ~30s)..."
    pushd frontend >/dev/null
    [[ -d node_modules ]] || npm install
    npm run build
    popd >/dev/null
fi

# --- Launch ------------------------------------------------------------------
echo
echo "============================================================================"
echo "  gpt-image2 starting on http://localhost:${PORT}"
echo "  (open the URL in your browser; press Ctrl+C to stop)"
echo "============================================================================"
echo

# Try to open browser (best-effort)
if [[ "$OSTYPE" == "darwin"* ]]; then
    (sleep 2 && open "http://localhost:${PORT}/") &
elif command -v xdg-open >/dev/null 2>&1; then
    (sleep 2 && xdg-open "http://localhost:${PORT}/") &
fi

exec "$VENV/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --app-dir backend
