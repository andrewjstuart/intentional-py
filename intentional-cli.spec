# -*- mode: python ; coding: utf-8 -*-
# The GUI ships separately as intentional.exe, so its packages are left out of the CLI.
import sys

if sys.platform != "win32":
    raise SystemExit("intentional-cli.spec builds the Windows executable (intentional-cli.exe) only; run it on Windows.")


a = Analysis(
    ['src/intentional_py/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['customtkinter', 'darkdetect', 'tkinter', 'intentional_py.gui'],
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
    name='intentional-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
