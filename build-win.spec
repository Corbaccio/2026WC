# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec — LaybackPassion.exe (Windows)"""

import os

block_cipher = None

a = Analysis(
    ["run.py"],
    pathex=[os.getcwd()],
    datas=[("web/templates", "web/templates")],
    hiddenimports=[
        "playwright.sync_api",
        "flask",
        "requests",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "numpy", "scipy", "PIL",
        "pandas", "lxml", "cryptography", "PyQt5", "sphinx",
        "IPython", "jedi", "parso", "pygments", "wcwidth",
    ],
    win_no_prefer_redirects=False,
    noarchive=False,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="LaybackPassion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
