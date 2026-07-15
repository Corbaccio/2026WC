# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec — 世界杯.app (onedir mode)"""

import os

block_cipher = None

datas = [
    ("web/templates", "web/templates"),
]

a = Analysis(
    ["run.py"],
    pathex=[os.getcwd()],
    datas=datas,
    hiddenimports=[
        "playwright.sync_api",
        "flask",
        "requests",
        "bs4",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "pandas",
        "lxml",
        "cryptography",
        "PyQt5",
        "sphinx",
        "setuptools._distutils",
    ],
    win_no_prefer_redirects=False,
    noarchive=False,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="LaybackPassion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="LaybackPassion",
)

app = BUNDLE(
    coll,
    name="LaybackPassion.app",
    icon=None,
    bundle_identifier="com.laybackpassion.app",
    info_plist={
        "NSHighResolutionCapable": "True",
        "CFBundleDisplayName": "LaybackPassion",
        "CFBundleShortVersionString": "1.0",
    },
)
