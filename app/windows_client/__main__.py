"""DeskPulse Windows Desktop Client - Main Entry Point."""
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Version
__version__ = '1.0.0'

# Import Windows client modules
from app.windows_client.config import (
    load_config,
    save_config,
    watch_config_changes,
    validate_backend_url,
    get_config_path
)

# Conditional imports for Windows-only features
try:
    import ctypes
    import win32event
    import win32api
    import winerror
    import requests
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    # Only exit if running as main, not on import (for testing on Linux)
    if __name__ == '__main__':
        print("ERROR: Windows-specific modules not available")
        print("Required: pywin32, requests")
        sys.exit(1)

logger = logging.getLogger('deskpulse.windows.main')


def setup_logging():
    """
    Configure logging with rotation.

    Creates log directory at %APPDATA%/DeskPulse/logs (or %TEMP% fallback).
    Uses RotatingFileHandler (10MB max, 5 backups).
    Format matches backend: %(asctime)s - %(name)s - %(levelname)s - %(message)s
    """
    # Determine log directory (same logic as config)
    appdata = os.getenv('APPDATA')
    if appdata:
        log_dir = Path(appdata) / 'DeskPulse' / 'logs'
    else:
        log_dir = Path(os.getenv('TEMP', '/tmp')) / 'DeskPulse' / 'logs'

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        # Fall back to TEMP
        log_dir = Path(os.getenv('TEMP', '/tmp')) / 'DeskPulse' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / 'client.log'

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            ),
            logging.StreamHandler()  # Console output for development
        ]
    )

    logger.info(f"Logging configured: {log_file}")


def check_single_instance():
    """
    Prevent multiple instances using Windows named mutex.

    Returns:
        mutex handle if successful, exits if instance already running
    """
    try:
        mutex = win32event.CreateMutex(None, False, 'Global\\DeskPulse')
        last_error = win32api.GetLastError()

        if last_error == winerror.ERROR_ALREADY_EXISTS:
            ctypes.windll.user32.MessageBoxW(
                0,
                "DeskPulse is already running.",
                "DeskPulse",
                0  # MB_OK
            )
            logger.info("Another instance is already running, exiting")
            sys.exit(0)

        logger.info("Single instance check passed")
        return mutex
    except Exception as e:
        logger.warning(f"Could not check single instance: {e}")
        return None


def validate_backend_reachable(backend_url: str) -> bool:
    """
    Check if backend is reachable with HTTP HEAD request.

    Args:
        backend_url: Backend URL to check

    Returns:
        bool: True if reachable, False otherwise
    """
    try:
        response = requests.head(backend_url, timeout=5)
        if response.status_code < 500:
            logger.info(f"Backend reachable: {backend_url}")
            return True
        else:
            logger.warning(f"Backend returned {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Backend not reachable: {e}")

        # Show troubleshooting dialog
        message = (
            f"Cannot reach DeskPulse backend:\n\n"
            f"{backend_url}\n\n"
            f"Troubleshooting:\n"
            f"1. Check Raspberry Pi power and network\n"
            f"2. Verify backend URL in config:\n"
            f"   {get_config_path()}\n"
            f"3. Test connection: ping {backend_url.split('//')[1].split(':')[0]}\n\n"
            f"Error: {e}"
        )

        ctypes.windll.user32.MessageBoxW(
            0,
            message,
            "DeskPulse - Backend Unreachable",
            0  # MB_OK
        )

        return False


def shutdown_handler(signum, frame):
    """
    Handle shutdown signal (SIGTERM).

    Gracefully exits application.
    """
    logger.info(f"Shutdown signal received: {signum}")
    sys.exit(0)


def config_watcher_thread(config_path: Path, socketio_client):
    """
    Watch config file for changes and reconnect if modified.

    Runs in daemon thread, checks every 10 seconds.

    Args:
        config_path: Path to config file
        socketio_client: SocketIO client instance to reconnect
    """
    logger.info("Config watcher thread started")

    while True:
        try:
            time.sleep(10)  # Check every 10 seconds

            if watch_config_changes():
                logger.info("Config file modified, reloading...")

                # Reload config
                new_config = load_config()
                new_backend_url = new_config['backend_url']

                # Disconnect from old backend
                socketio_client.disconnect()

                # Update backend URL
                socketio_client.backend_url = new_backend_url
                socketio_client.tray_manager.backend_url = new_backend_url

                # Reconnect to new backend
                socketio_client.connect()

                logger.info(f"Reconnected to new backend: {new_backend_url}")

        except Exception as e:
            logger.error(f"Error in config watcher: {e}")


def main():
    """
    Main entry point for Windows desktop client.

    - Sets up logging
    - Checks single instance
    - Loads and validates config
    - Validates backend reachability
    - Creates SocketIO client and TrayManager
    - Starts config watcher thread
    - Runs tray icon (blocking)
    """
    # Check Windows availability
    if not WINDOWS_AVAILABLE:
        print("ERROR: Windows-specific modules not available")
        print("Required: pywin32, requests")
        sys.exit(1)

    # Setup logging first
    setup_logging()
    logger.info(f"DeskPulse Windows Client v{__version__} starting")

    # Check single instance
    mutex = check_single_instance()

    try:
        # Load and validate config
        try:
            config = load_config()
            backend_url = config['backend_url']
            logger.info(f"Config loaded: backend_url={backend_url}")
        except ValueError as e:
            # Backend URL validation failed
            logger.error(f"Invalid backend URL in config: {e}")
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Invalid Backend URL\n\n{e}\n\n"
                f"Please edit config file:\n{get_config_path()}\n\n"
                f"Example: http://raspberrypi.local:5000",
                "DeskPulse - Configuration Error",
                0  # MB_OK
            )
            sys.exit(1)

        # Validate backend reachable (startup check)
        if not validate_backend_reachable(backend_url):
            logger.error("Backend not reachable, exiting")
            sys.exit(1)

        # Register shutdown handler
        signal.signal(signal.SIGTERM, shutdown_handler)

        # Import TrayManager, SocketIOClient, and WindowsNotifier (after logging setup)
        from app.windows_client.socketio_client import SocketIOClient
        from app.windows_client.tray_manager import TrayManager
        from app.windows_client.notifier import WindowsNotifier

        # Create TrayManager first (SocketIO client needs reference)
        tray_manager = TrayManager(backend_url, socketio_client=None)

        # Create WindowsNotifier (Story 7.2)
        notifier = WindowsNotifier(tray_manager)

        # Create SocketIO client with notifier
        socketio_client = SocketIOClient(backend_url, tray_manager, notifier)

        # Update tray_manager with socketio_client reference
        tray_manager.socketio_client = socketio_client

        # Start config watcher thread
        watcher = threading.Thread(
            target=config_watcher_thread,
            args=(get_config_path(), socketio_client),
            daemon=True,
            name='ConfigWatcher'
        )
        watcher.start()

        # Connect SocketIO in background thread
        connect_thread = threading.Thread(
            target=socketio_client.connect,
            daemon=True,
            name='SocketIOConnect'
        )
        connect_thread.start()

        # Run TrayManager (blocking call)
        logger.info("Starting tray manager")
        tray_manager.run()

        # Cleanup on exit
        logger.info("Tray manager stopped, cleaning up")

        # Shutdown notifier queue thread (Story 7.2)
        if notifier:
            notifier.shutdown()

        socketio_client.disconnect()

        # Flush logs
        for handler in logging.root.handlers:
            handler.flush()

        logger.info("DeskPulse Windows client exited cleanly")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")

        # Show error dialog
        ctypes.windll.user32.MessageBoxW(
            0,
            f"DeskPulse encountered a fatal error:\n\n{e}\n\nCheck logs for details.",
            "DeskPulse - Fatal Error",
            0  # MB_OK
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
