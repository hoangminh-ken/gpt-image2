# Setup Guide — Run gpt-image2 on Another Machine

Two distribution options:

| Mode | Best for | Size | Prereqs on target |
|------|---------|------|-------------------|
| **A. Standalone `.exe`** (Windows) | End users — zero setup | ~33 MB single file | Just Windows 10/11 (WebView2 ships with Edge) |
| **B. Source + launcher** | Devs / cross-platform | ~30 MB source | Python 3.10+, Node 20+ |

→ Pick **A** unless you need to modify code or run on macOS/Linux.

---

## Option A — Distribute the standalone .exe

### Build (one-time, on dev machine)

```cmd
build-exe.bat
```

This:
1. Builds the frontend (`npm run build`)
2. Bundles backend + frontend + Python runtime via PyInstaller
3. Outputs `dist/gpt-image2.exe` (~33 MB)

### Distribute

Send `dist/gpt-image2.exe` to the target user. That's it — one file.

### First run on target machine

1. Double-click `gpt-image2.exe`
2. App creates `%APPDATA%\gpt-image2\.env` with empty key
3. Open that `.env` in Notepad, paste:
   ```
   OPENAI_API_KEY=sk-proj-...your-key-here...
   ```
4. Save and close `.env`, then re-launch `gpt-image2.exe`
5. Native window opens with the dashboard

### Where data lives (Option A)

```
%APPDATA%\gpt-image2\
├── .env                    ← your API key
├── data\
│   ├── app.db              ← job history
│   └── uploads\            ← drag-dropped refs
└── outputs\                ← generated images
```

To **uninstall**: delete the `.exe` and the `%APPDATA%\gpt-image2` folder.

---

## Option B — Source + launcher (dev mode)

This guide walks you through installing and running gpt-image2 on a fresh Windows / macOS / Linux machine.

---

## TL;DR

```text
1. Install Python 3.10+ and Node.js 20+
2. Clone or copy the project to your new machine
3. Edit  backend/.env  → paste your OPENAI_API_KEY
4. Double-click  start.bat  (Windows)  or  ./start.sh  (macOS/Linux)
5. Browser opens to http://localhost:8767
```

The launcher auto-installs dependencies and builds the frontend on first run, then serves the app from a single uvicorn process.

---

## 1. Prerequisites

| Tool | Min version | Check | Download |
|------|-------------|-------|----------|
| **Python** | 3.10 | `python --version` | <https://www.python.org/downloads/> |
| **Node.js** | 20 LTS | `node --version` | <https://nodejs.org/> |
| **Git** *(optional)* | any | `git --version` | <https://git-scm.com/downloads> — only if cloning vs copying ZIP |
| **OpenAI API key** | — | <https://platform.openai.com/api-keys> | needs `gpt-image-2` access |

> **Windows tip:** during Python install, tick **"Add Python to PATH"**. After install, open a fresh terminal and run `python --version` to confirm.

---

## 2. Get the code (pick one)

### Option A — Clone from GitHub (easiest if you have git)

```bash
git clone https://github.com/hoangminh-ken/gpt-image2.git
cd gpt-image2
```

### Option B — Copy from your current machine

1. On the source machine, copy the folder `gpt-image2/` to a USB / network share, **excluding**:
   - `backend/.venv/` *(will be recreated)*
   - `frontend/node_modules/` *(will be recreated)*
   - `frontend/dist/` *(will be rebuilt)*
   - `data/`, `outputs/` *(local job state — only copy if you want to bring history)*
   - `backend/.env` *(do NOT copy — contains your API key; we'll set it up fresh on target)*
2. Paste onto the target machine. Final folder size should be ~30MB (just source).

---

## 3. Configure the API key

```bash
cd gpt-image2
```

The launcher will create `backend/.env` from `backend/.env.example` automatically on first run. After it does, edit that file:

```ini
OPENAI_API_KEY=sk-proj-...           # paste your key here
OPENAI_ADMIN_KEY=                    # optional — for cost reconcile (org admin scope)
OPENAI_IMAGE_MODEL=gpt-image-2       # default; can pin to gpt-image-2-2026-04-21
DEFAULT_CONCURRENCY=5                # parallel API calls
MAX_REF_DIMENSION=2048               # auto-resize ref images larger than this
HOST=127.0.0.1                       # localhost only (do NOT change without auth)
PORT=8000                            # ignored by launcher; launcher uses 8767
```

Save the file.

---

## 4. Run

### Windows

Double-click **`start.bat`** in File Explorer, or run from terminal:

```cmd
.\start.bat
```

### macOS / Linux

```bash
./start.sh
```

> If permission denied: `chmod +x start.sh` then retry.

### What happens on first run

1. Checks Python + Node are on PATH
2. Creates `backend/.venv` and installs Python deps (~30s)
3. Runs `npm install` in `frontend/` (~60s)
4. Builds frontend with Vite → `frontend/dist/` (~10s)
5. Starts uvicorn on `http://localhost:8767`
6. Auto-opens your default browser

Subsequent runs skip steps 2-4 — startup is ~3 seconds.

### Stopping

Close the terminal window (Windows) or press `Ctrl+C` (Unix).

---

## 5. Using the tool

| URL | What |
|-----|------|
| `http://localhost:8767/` | Dashboard |
| `http://localhost:8767/jobs/new` | Create job (Mode A: template + refs / Mode B: Excel) |
| `http://localhost:8767/history` | All past jobs with filters + Open folder |
| `http://localhost:8767/cost` | Cost dashboard + reconcile vs OpenAI Usage |
| `http://localhost:8767/settings` | View config + test API key |

Generated images land in `outputs/{job_id}/`. Click **Open folder** in the UI to jump to them in Explorer/Finder.

---

## 6. Where data lives

```text
gpt-image2/
├── backend/.env            ← your API key (NEVER commit/share this file)
├── data/
│   ├── app.db              ← SQLite job history
│   └── uploads/            ← drag-dropped reference images
├── outputs/                ← generated PNG images per job
└── frontend/dist/          ← built UI (regenerated on update)
```

To **reset everything**, delete `data/` and `outputs/`. To **back up** job history, copy these two folders.

---

## 7. Updating to a newer version

```bash
git pull
# delete cached build to force rebuild on next launch
rmdir /s /q frontend\dist           # Windows
rm -rf frontend/dist                # Unix
# update Python deps if requirements changed
backend\.venv\Scripts\pip install -r backend\requirements.txt   # Windows
backend/.venv/bin/pip install -r backend/requirements.txt       # Unix
# relaunch
.\start.bat                         # or ./start.sh
```

---

## 8. Troubleshooting

| Symptom | Fix |
|---------|-----|
| `python` not found | Reinstall Python with "Add to PATH" checked. Open a fresh terminal. |
| `node` not found | Install Node 20+ from nodejs.org. Open a fresh terminal. |
| `[ERROR] pip install failed` | Check internet; corporate proxy may block PyPI. Set `HTTPS_PROXY` env var if needed. |
| Browser doesn't open | Open `http://localhost:8767/` manually. |
| Port 8767 already in use | Edit `start.bat` / `start.sh` and change `PORT=` to e.g. `8768`. |
| `OPENAI_API_KEY not configured` | Edit `backend/.env`, paste key after `OPENAI_API_KEY=`, no quotes. Restart. |
| 401 from OpenAI | Key invalid/expired. Test in **Settings** page → "Test key". |
| 429 rate limit | Lower `DEFAULT_CONCURRENCY` in `.env` (try 2–3). Restart. |
| Job stuck "running" after crash | Just restart `start.bat` — server resumes pending items automatically. |
| Frontend looks unstyled | Rebuild: delete `frontend/dist/` and rerun. |
| `Module not found` errors | Delete `backend/.venv/` and `frontend/node_modules/`, rerun launcher. |

---

## 9. Cost expectations

Per OpenAI pricing (verified May 2026):
- **gpt-image-2**: $8/M input tokens, $30/M output tokens
- **Typical 1024×1024 medium-quality image with one reference**: ~$0.07
- 100 images ≈ $7

The Dashboard shows real-time spend. The Cost page can reconcile against OpenAI's own usage records (requires `OPENAI_ADMIN_KEY`).

---

## 10. Security notes (important if not on a trusted machine)

- This tool binds to `127.0.0.1` only — **not reachable over LAN/internet** by default. Do not change `HOST` to `0.0.0.0` unless you add authentication.
- `backend/.env` contains your raw API key. Anyone who reads this file can spend on your OpenAI account.
- The tool has **no login**. Anyone with terminal access to the machine can launch it and use your key.
- `/api/preview` allows reading any image file on disk (deliberately permissive for ref previews); fine for local use, never expose to internet.

If you need multi-user / remote access, this tool needs a security refactor — see project README "Out of scope".

---

Happy generating!
