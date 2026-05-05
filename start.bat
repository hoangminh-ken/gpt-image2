@echo off
REM ============================================================================
REM gpt-image2 — Windows one-click launcher
REM Auto-installs deps on first run, builds frontend, launches single-process
REM uvicorn server (serves both API and SPA on http://localhost:8767)
REM ============================================================================

setlocal enableextensions
cd /d "%~dp0"

set "PORT=8767"
set "VENV=backend\.venv"
set "DIST=frontend\dist"

REM --- Pre-flight checks --------------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not on PATH. Install Python 3.10+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not on PATH. Install Node.js 20+ from https://nodejs.org/
    pause
    exit /b 1
)

if not exist "backend\.env" (
    echo [SETUP] backend\.env not found. Creating from .env.example...
    copy /Y "backend\.env.example" "backend\.env" >nul
    echo.
    echo [ACTION REQUIRED] Open backend\.env in a text editor and paste your OpenAI API key:
    echo     OPENAI_API_KEY=sk-...
    echo.
    echo Then re-run start.bat.
    pause
    exit /b 0
)

REM --- Bootstrap Python venv ---------------------------------------------------
if not exist "%VENV%\Scripts\python.exe" (
    echo [SETUP] Creating Python virtual environment...
    python -m venv %VENV%
    if errorlevel 1 ( echo [ERROR] venv creation failed & pause & exit /b 1 )
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV%\Scripts\python.exe" -m pip install -r backend\requirements.txt
    if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )
)

REM --- Build frontend if needed ------------------------------------------------
if not exist "%DIST%\index.html" (
    echo [SETUP] Building frontend ^(first run, ~30s^)...
    pushd frontend
    if not exist "node_modules" (
        call npm install
        if errorlevel 1 ( echo [ERROR] npm install failed & popd & pause & exit /b 1 )
    )
    call npm run build
    if errorlevel 1 ( echo [ERROR] frontend build failed & popd & pause & exit /b 1 )
    popd
)

REM --- Launch ------------------------------------------------------------------
echo.
echo ============================================================================
echo   gpt-image2 starting on http://localhost:%PORT%
echo   ^(opens browser automatically; close this window to stop the server^)
echo ============================================================================
echo.

start "" http://localhost:%PORT%/

"%VENV%\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT% --app-dir backend
