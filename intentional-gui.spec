# -*- mode: python ; coding: utf-8 -*-
# CustomTkinter's theme files are collected by the hook in pyinstaller-hooks-contrib.
import sys

if sys.platform != "win32":
    raise SystemExit("intentional-gui.spec builds the Windows executable (intentional.exe) only; run it on Windows.")

sys.path.insert(0, SPECPATH)
from version_info import version_resource  # noqa: E402


a = Analysis(
    ['src/intentional_py/gui/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['typer'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='intentional',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_resource('intentional', 'Intentional - Dialogflow ES intent builder'),
)
