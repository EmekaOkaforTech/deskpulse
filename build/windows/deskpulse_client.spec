# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DeskPulse Windows Desktop Client.

Creates standalone executable with all dependencies bundled.
No Python installation required on target machine.
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(SPECPATH, '..', '..'))
sys.path.insert(0, project_root)

block_cipher = None

a = Analysis(
    ['../../app/windows_client/__main__.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('../../assets/windows/icon_professional.ico', 'assets/windows'),
        ('../../app/windows_client/config.py', 'app/windows_client'),
    ],
    hiddenimports=[
        'engineio.async_drivers.threading',
        'PIL._tkinter_finder',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'Flask',
        'flask_socketio',
        'cv2',
        'numpy',
        'sqlite3',
        'matplotlib',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DeskPulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../../assets/windows/icon_professional.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DeskPulse',
)
