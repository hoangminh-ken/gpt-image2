# PyInstaller spec for gpt-image2 desktop bundle.
# Build: from project root, run `python -m PyInstaller gpt-image2.spec`
# Output: dist/gpt-image2.exe (Windows) — single-file ~120MB.

# noqa: E501

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT = Path('.').resolve()
DIST = PROJECT / 'frontend' / 'dist'
ICON = None  # set to a .ico/.icns path later if you have one

if not (DIST / 'index.html').exists():
    raise SystemExit('frontend/dist/index.html not found. Run `npm run build` in frontend/ first.')

hidden = (
    collect_submodules('uvicorn')
    + collect_submodules('fastapi')
    + collect_submodules('starlette')
    + collect_submodules('pydantic')
    + collect_submodules('pydantic_settings')
    + collect_submodules('openai')
    + collect_submodules('httpx')
    + collect_submodules('webview')
    + collect_submodules('openpyxl')
    + collect_submodules('PIL')
    + ['app.main', 'app.desktop']
)

datas = []
# Bundle the built SPA so backend can serve it from sys._MEIPASS/frontend/dist
datas += [(str(DIST), 'frontend/dist')]
# webview platform implementations
try:
    datas += collect_data_files('webview')
except Exception:
    pass


a = Analysis(
    ['backend/app/desktop.py'],
    pathex=[str(PROJECT / 'backend')],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy.random', 'pytest'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gpt-image2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # no console window in production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)
