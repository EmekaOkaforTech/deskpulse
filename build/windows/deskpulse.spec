# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DeskPulse Windows desktop client.

This spec creates a one-folder distribution (--onedir mode) for:
- Faster startup (no temp extraction)
- Fewer antivirus false positives
- Easier debugging
- Better for enterprise deployment

Build with: pyinstaller build/windows/deskpulse.spec
"""

block_cipher = None

a = Analysis(
    ['app/windows_client/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Application icon (bundled in assets/)
        ('assets/windows/icon.ico', 'assets'),
    ],
    hiddenimports=[
        # System tray (pystray)
        'pystray',
        'pystray._win32',

        # Image handling (Pillow)
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',

        # Toast notifications (winotify - modern replacement for win10toast)
        'winotify',
        'winotify.audio',

        # Windows API (pywin32)
        'win32event',
        'win32api',
        'winerror',

        # SocketIO client
        'socketio',
        'socketio.client',
        'engineio',
        'engineio.client',
        'engineio.async_threading',

        # HTTP client
        'requests',
        'requests.adapters',
        'urllib3',

        # Standard library (may need explicit inclusion)
        'queue',
        'threading',
        'json',
        'logging',
        'logging.handlers',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Backend-only packages (not needed in Windows client)
        'flask',           # Backend web framework
        'flask_socketio',  # Backend SocketIO
        'opencv-python',   # Backend CV processing
        'cv2',
        'mediapipe',       # Backend pose detection
        'numpy',           # May be required by Pillow - test before excluding
        'sdnotify',        # Backend systemd integration
        'schedule',        # Backend scheduling
        'systemd',         # Backend service

        # Development/testing packages
        'pytest',
        'pytest-asyncio',
        'unittest',

        # Documentation
        'sphinx',
        'docutils',
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
    exclude_binaries=True,  # One-folder mode (--onedir)
    name='DeskPulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression (~25-40% size reduction)
    console=False,  # Windowed GUI application (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/windows/icon.ico',  # Application icon for .exe
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
