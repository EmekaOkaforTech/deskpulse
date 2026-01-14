# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DeskPulse Standalone Windows Edition.

Creates standalone executable with FULL BACKEND bundled (Flask, OpenCV, MediaPipe).
No Python installation or Raspberry Pi required on target machine.

CRITICAL FIXES (2026-01-12):
- Bundle entire app package (app/__init__.py, app/api/, app/cv/, etc.)
- Use PyInstaller hooks for cv2, mediapipe, numpy collection
- Include socketio.client/engineio.client (required by socketio package internally)
- Explicit app/config.py bundling

Distribution size: ~200-300 MB (Story 8.6 validation: 203.4 MB)
"""

import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(SPECPATH, '..', '..'))
sys.path.insert(0, project_root)

block_cipher = None

# Collect backend libraries using PyInstaller hooks (CRITICAL for 200+ MB dist)
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# OpenCV - cv2.pyd (70.9 MB) + opencv_videoio_ffmpeg DLL (28.3 MB)
cv2_datas = collect_data_files('cv2')
cv2_binaries = collect_dynamic_libs('cv2')

# MediaPipe - pose detection models (Tasks API 0.10.31 x64)
mediapipe_datas = collect_data_files('mediapipe')
mediapipe_binaries = collect_dynamic_libs('mediapipe')

# NumPy - core numeric library
numpy_datas = collect_data_files('numpy')

a = Analysis(
    ['../../app/standalone/__main__.py'],  # Story 8.5 entry point
    pathex=[project_root],

    # Backend DLLs (cv2, mediapipe) - REQUIRED for 200+ MB bundle
    binaries=cv2_binaries + mediapipe_binaries,

    datas=[
        # Application icon (multi-resolution)
        ('../../assets/windows/icon_professional.ico', 'assets/windows'),

        # ENTIRE app package (includes __init__.py, api/, cv/, extensions.py, etc.)
        # This ensures Flask factory (create_app) is bundled
        ('../../app', 'app'),
    ] + cv2_datas + mediapipe_datas + numpy_datas,

    hiddenimports=[
        # === Core Application (Story 8.5) ===
        'app.standalone.__main__',
        'app.standalone.backend_thread',
        'app.standalone.tray_app',
        'app.standalone.config',

        # === Windows Integration (Story 8.3) ===
        'app.standalone.camera_windows',
        'app.standalone.camera_selection_dialog',
        'app.standalone.camera_permissions',
        'app.standalone.camera_error_handler',

        # === Tkinter for Camera Selection Dialog ===
        'tkinter',
        'tkinter.ttk',

        # === Backend Framework (INCLUDED - Story 8.1) ===
        'flask',
        'flask.app',
        'flask.blueprints',
        'flask.templating',
        'flask.json',
        'flask.helpers',

        # Flask-SocketIO (INCLUDED - for optional web dashboard)
        # NOTE: app/__init__.py uses try/except import (lines 10-13)
        'flask_socketio',
        'socketio',
        'socketio.server',
        'socketio.client',  # REQUIRED - socketio package imports internally
        'engineio',
        'engineio.server',
        'engineio.client',  # REQUIRED - socketio package imports internally

        # Flask-Talisman (REQUIRED - unconditional import in app/__init__.py)
        'flask_talisman',

        # Flask-SQLAlchemy
        'flask_sqlalchemy',

        # === App Core Modules ===
        'app',  # Main app package
        'app.config',  # Configuration classes
        'app.extensions',  # Database, SocketIO init
        'app.core',  # Logging configuration

        # === Backend API (Story 8.1) ===
        'app.api',
        'app.api.routes',

        # === CV Pipeline (Story 8.2) ===
        'app.cv',
        'app.cv.pipeline',

        # === Computer Vision (INCLUDED - Story 8.2/8.3) ===
        'cv2',
        'cv2.data',  # Haar cascades, models

        # MediaPipe - EXACT VERSION REQUIRED (Story 8.2 Tasks API migration)
        # requirements.txt locks versions:
        #   - x64/AMD64: mediapipe==0.10.31
        #   - ARM64: mediapipe==0.10.18
        'mediapipe',
        'mediapipe.python',
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.vision.pose_landmarker',

        # NumPy
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',

        # === System Tray (Story 8.5) ===
        'pystray',
        'pystray._win32',

        # === Image Processing ===
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',

        # === Toast Notifications (Story 8.5) ===
        'winotify',
        'winotify.audio',

        # === Windows API (Story 8.5) ===
        'win32event',
        'win32api',
        'win32con',
        'winerror',
        'ctypes',
        'ctypes.wintypes',

        # === Database ===
        'sqlite3',
        'sqlalchemy',
        'sqlalchemy.orm',
        'sqlalchemy.ext',
        'sqlalchemy.ext.declarative',

        # === Standard Library (explicit inclusion) ===
        'queue',
        'threading',
        'json',
        'logging',
        'logging.handlers',
        'pathlib',
        'datetime',
        'time',
        'signal',
        'enum',
        'dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Development/testing (never bundle)
        'pytest',
        'pytest-cov',
        'pytest-flask',
        'unittest',
        'test',
        'tests',

        # Documentation
        'sphinx',
        'docutils',

        # Linux-only packages
        'systemd',
        'systemd.journal',
        'sdnotify',

        # Unnecessary GUI frameworks
        'tkinter',  # We use native Windows dialogs
        'wx',
        'PyQt5',
        'PyQt6',

        # Matplotlib (not needed for standalone)
        'matplotlib',
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
    exclude_binaries=True,  # One-folder mode (faster startup, fewer AV issues)
    name='DeskPulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # UPX compression (~25-40% size reduction)
    console=True,  # TEMPORARY: Enable console for debugging (change to False for production)
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
    upx=True,  # UPX compression on DLLs
    upx_exclude=[],
    name='DeskPulse-Standalone',
)
