"""
PyInstaller hook to prevent importing server-side app/__init__.py

Replaces app/__init__.py with empty stub to avoid flask_talisman dependency.
"""
from PyInstaller.utils.hooks import collect_submodules

# Only include windows_client submodules, exclude all server code
hiddenimports = [
    'app.windows_client',
    'app.windows_client.config',
    'app.windows_client.socketio_client',
    'app.windows_client.tray_manager',
    'app.windows_client.notifier',
]

# Exclude server modules
excludedimports = [
    'app.main',
    'app.api',
    'app.cv',
    'app.core',
    'app.extensions',
    'app.config',
    'flask',
    'flask_socketio',
    'flask_talisman',
]
