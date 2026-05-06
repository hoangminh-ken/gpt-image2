@echo off
REM ============================================================================
REM Build a single-file Windows .exe for gpt-image2.
REM Output: dist\gpt-image2.exe
REM ============================================================================

setlocal enableextensions
cd /d "%~dp0"

set "VENV=backend\.venv"

REM --- Pre-flight --------------------------------------------------------------
if not exist "%VENV%\Scripts\python.exe" (
    echo [ERROR] backend\.venv missing. Run start.bat once to bootstrap, or:
    echo     python -m venv %VENV% ^&^& %VENV%\Scripts\pip install -r backend\requirements.txt
    exit /b 1
)

where node >nul 2>&1 || ( echo [ERROR] Node not on PATH & exit /b 1 )

REM --- Build frontend ----------------------------------------------------------
echo [BUILD] Building frontend...
pushd frontend
if not exist "node_modules" call npm install
call npm run build
if errorlevel 1 ( echo [ERROR] frontend build failed & popd & exit /b 1 )
popd

REM --- Clean prior build -------------------------------------------------------
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM --- PyInstaller -------------------------------------------------------------
echo [BUILD] Bundling .exe with PyInstaller...
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm gpt-image2.spec
if errorlevel 1 ( echo [ERROR] PyInstaller failed & exit /b 1 )

if not exist "dist\gpt-image2.exe" (
    echo [ERROR] Build did not produce dist\gpt-image2.exe
    exit /b 1
)

echo.
echo ============================================================================
echo   SUCCESS: dist\gpt-image2.exe
for %%I in (dist\gpt-image2.exe) do echo   Size: %%~zI bytes
echo.
echo   First run on a target machine:
echo     1. Double-click gpt-image2.exe
echo     2. App creates .env in %%APPDATA%%\gpt-image2\
echo     3. Paste OPENAI_API_KEY into that .env, restart .exe
echo ============================================================================
