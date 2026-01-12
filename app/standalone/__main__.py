"""
DeskPulse Standalone - Main Entry Point (Story 8.5).

Single-process Windows application combining backend and tray UI.
Backend runs in daemon thread, tray UI in main thread.

Architecture:
- Main Thread: Configuration → Backend startup → Tray UI (blocking)
- Backend Thread (daemon): Flask app → CV pipeline → Callbacks → Queue
- Consumer Thread (daemon): Queue consumer → Toast notifications → Icon updates

Enterprise Requirements:
- Single instance check (Windows mutex)
- Real backend connections (no mocks)
- Graceful shutdown (<2s)
- Comprehensive error handling
- Production logging to %APPDATA%
"""

import sys
import time
import queue
import logging
import signal
from pathlib import Path
from typing import Optional

# Windows-specific imports
try:
    import win32event
    import win32api
    import winerror
    import ctypes
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False
    print("ERROR: Windows-specific modules not available (win32event, win32api)")
    print("Install with: pip install pywin32")
    sys.exit(1)

# DeskPulse imports
from app.standalone.backend_thread import (
    BackendThread,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    PRIORITY_LOW
)
from app.standalone.tray_app import TrayApp
from app.standalone.config import (
    load_config,
    save_config,
    get_log_dir,
    get_appdata_dir,
    DEFAULT_CONFIG
)

logger = logging.getLogger('deskpulse.standalone.main')

# Application version
__version__ = "2.0.0"

# Single instance mutex name
MUTEX_NAME = 'Global\\DeskPulse'

# Error codes for MessageBox
MB_OK = 0x0
MB_ICONERROR = 0x10
MB_ICONWARNING = 0x30
MB_ICONINFORMATION = 0x40
MB_TOPMOST = 0x40000  # CRITICAL: Ensures dialog appears in foreground


def setup_logging():
    """
    Configure logging for standalone Windows edition.

    Logs to:
    - File: %APPDATA%/DeskPulse/logs/deskpulse.log (rotating, 10 MB, 5 backups)
    - Console: INFO level
    """
    from logging.handlers import RotatingFileHandler

    log_file = get_log_dir() / 'deskpulse.log'

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # INFO for production, not DEBUG

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)  # INFO for production
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"DeskPulse Standalone v{__version__} starting")
    logger.info(f"Logging configured: {log_file}")
    logger.info(f"Data directory: {get_appdata_dir()}")


def check_single_instance() -> Optional[int]:
    """
    Check if DeskPulse is already running using Windows mutex.

    Returns:
        mutex handle if successful, None if already running

    Displays MessageBox and exits if instance already exists.
    """
    try:
        # Create named mutex
        mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()

        if last_error == winerror.ERROR_ALREADY_EXISTS:
            logger.warning("DeskPulse is already running")

            # Show MessageBox with MB_TOPMOST
            ctypes.windll.user32.MessageBoxW(
                0,
                "DeskPulse is already running.\n\n"
                "Check your system tray for the DeskPulse icon.",
                "DeskPulse - Already Running",
                MB_OK | MB_ICONINFORMATION | MB_TOPMOST
            )

            return None

        logger.info("Single instance check passed - mutex acquired")
        return mutex

    except Exception as e:
        logger.error(f"Failed to create mutex: {e}")
        return None


def load_and_validate_config() -> dict:
    """
    Load configuration from %APPDATA%/DeskPulse/config.json.

    Returns:
        dict: Configuration dictionary

    Handles missing and corrupt config files gracefully.
    """
    try:
        config = load_config()
        logger.info("Configuration loaded successfully")

        # Validate critical fields
        if 'camera' not in config:
            logger.warning("Camera config missing, using defaults")
            config['camera'] = DEFAULT_CONFIG['camera']

        if 'monitoring' not in config:
            logger.warning("Monitoring config missing, using defaults")
            config['monitoring'] = DEFAULT_CONFIG['monitoring']

        # Add IPC section if missing (Story 8.5 - Task 3)
        if 'ipc' not in config:
            logger.info("Adding IPC section to config")
            config['ipc'] = {
                'event_queue_size': 150,
                'alert_latency_target_ms': 50,
                'metrics_log_interval_seconds': 60
            }
            save_config(config)

        return config

    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        logger.warning("Using DEFAULT_CONFIG")

        # Show warning MessageBox with MB_TOPMOST
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Failed to load configuration:\n{str(e)}\n\n"
            f"Using default configuration.",
            "DeskPulse - Configuration Warning",
            MB_OK | MB_ICONWARNING | MB_TOPMOST
        )

        return DEFAULT_CONFIG.copy()


def create_event_queue(config: dict) -> queue.PriorityQueue:
    """
    Create priority event queue for IPC.

    Args:
        config: Configuration dictionary

    Returns:
        PriorityQueue with configured maxsize
    """
    queue_size = config.get('ipc', {}).get('event_queue_size', 150)
    event_queue = queue.PriorityQueue(maxsize=queue_size)

    logger.info(f"Event queue created with maxsize={queue_size}")
    return event_queue


def register_callbacks(backend: BackendThread, event_queue: queue.PriorityQueue):
    """
    Register callback glue connecting backend events to queue.

    This is the CRITICAL integration point between backend and tray.
    Callbacks execute in backend thread and enqueue events for consumer.

    Args:
        backend: BackendThread instance
        event_queue: Priority queue for IPC
    """

    def on_alert_callback(duration: int, timestamp: str) -> None:
        """Handle alert event from backend."""
        try:
            event_queue.put((
                PRIORITY_CRITICAL,  # Highest priority
                time.perf_counter(),  # Enqueue timestamp for latency tracking
                'alert',
                {'duration': duration, 'timestamp': timestamp}
            ), timeout=1.0)  # Block up to 1s (CRITICAL never dropped)
            logger.debug(f"Alert event enqueued: duration={duration}s")
        except queue.Full:
            logger.error("Alert event dropped - queue full (CRITICAL should never drop!)")

    def on_correction_callback(previous_duration: int, timestamp: str) -> None:
        """Handle correction event from backend."""
        try:
            event_queue.put((
                PRIORITY_NORMAL,  # Normal priority
                time.perf_counter(),
                'correction',
                {'previous_duration': previous_duration, 'timestamp': timestamp}
            ), timeout=0.5)  # Block up to 0.5s
            logger.debug(f"Correction event enqueued: previous_duration={previous_duration}s")
        except queue.Full:
            logger.warning("Correction event dropped - queue full")

    def on_status_change_callback(monitoring_active: bool, threshold_seconds: int) -> None:
        """Handle status change event from backend."""
        try:
            event_queue.put((
                PRIORITY_HIGH,  # High priority
                time.perf_counter(),
                'status_change',
                {'monitoring_active': monitoring_active, 'threshold_seconds': threshold_seconds}
            ), timeout=0.5)
            logger.debug(f"Status change event enqueued: monitoring_active={monitoring_active}")
        except queue.Full:
            logger.warning("Status change event dropped - queue full")

    def on_camera_state_callback(state: str, timestamp: str) -> None:
        """Handle camera state event from backend."""
        try:
            event_queue.put((
                PRIORITY_HIGH,  # High priority
                time.perf_counter(),
                'camera_state',
                {'state': state, 'timestamp': timestamp}
            ), timeout=0.5)
            logger.debug(f"Camera state event enqueued: state={state}")
        except queue.Full:
            logger.warning("Camera state event dropped - queue full")

    def on_error_callback(message: str, error_type: str) -> None:
        """Handle error event from backend."""
        try:
            event_queue.put((
                PRIORITY_CRITICAL,  # Critical priority
                time.perf_counter(),
                'error',
                {'message': message, 'error_type': error_type}
            ), timeout=1.0)
            logger.debug(f"Error event enqueued: {error_type} - {message}")
        except queue.Full:
            logger.error("Error event dropped - queue full (CRITICAL should never drop!)")

    # Register all callbacks
    backend.register_callback('alert', on_alert_callback)
    backend.register_callback('correction', on_correction_callback)
    backend.register_callback('status_change', on_status_change_callback)
    backend.register_callback('camera_state', on_camera_state_callback)
    backend.register_callback('error', on_error_callback)

    logger.info("All 5 callbacks registered successfully")


def setup_signal_handlers(backend: BackendThread, tray_app: Optional[TrayApp]):
    """
    Setup signal handlers for graceful shutdown.

    Args:
        backend: BackendThread instance
        tray_app: TrayApp instance (may be None if not started yet)
    """
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")

        if tray_app:
            tray_app.stop()

        backend.stop()

        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.debug("Signal handlers registered (SIGTERM, SIGINT)")


def main():
    """
    Main entry point for DeskPulse Standalone.

    Orchestrates entire application lifecycle:
    1. Setup logging
    2. Single instance check
    3. Load configuration
    4. Create event queue
    5. Start backend thread
    6. Register callbacks (glue)
    7. Start tray app (blocking)
    8. Graceful shutdown cleanup
    """
    mutex = None
    backend = None
    tray_app = None

    try:
        # Step 1: Setup logging
        setup_logging()
        logger.info("=" * 60)
        logger.info(f"DeskPulse Standalone v{__version__} - Starting")
        logger.info("=" * 60)

        # Step 2: Single instance check
        mutex = check_single_instance()
        if mutex is None:
            logger.warning("Exiting - instance already running")
            sys.exit(0)

        # Step 3: Load configuration
        config = load_and_validate_config()

        # Step 4: Create event queue
        event_queue = create_event_queue(config)

        # Step 5: Initialize and start backend thread
        logger.info("Initializing backend thread...")
        backend = BackendThread(config, event_queue=event_queue)
        backend.start()

        # Wait for Flask app initialization with proper polling (not arbitrary sleep)
        # CRITICAL: Windows camera (MSMF) takes 5-30 seconds to initialize
        logger.info("Waiting for backend initialization (camera startup may take 5-30 seconds)...")
        MAX_WAIT_SECONDS = 35.0  # Increased for MSMF camera initialization
        POLL_INTERVAL = 0.1  # Check every 100ms

        start_time = time.time()
        while backend.flask_app is None and (time.time() - start_time) < MAX_WAIT_SECONDS:
            time.sleep(POLL_INTERVAL)

        elapsed = time.time() - start_time

        # Verify initialization
        if backend.flask_app is None:
            error_msg = f"Backend failed to initialize within {MAX_WAIT_SECONDS}s - Flask app is None"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f"Backend initialized successfully in {elapsed:.2f}s")
        logger.info(f"Flask app type: {type(backend.flask_app)}")
        logger.info(f"Backend running: {backend.running}")

        logger.info("Backend thread started successfully")

        # Step 6: Register callbacks (glue code)
        logger.info("Registering callbacks...")
        register_callbacks(backend, event_queue)
        logger.info("Callbacks registered successfully")

        # Step 7: Initialize tray app
        logger.info("Initializing tray application...")
        try:
            tray_app = TrayApp(backend, event_queue)
            logger.info("TrayApp instance created successfully")
        except Exception as tray_init_error:
            logger.exception(f"FATAL: TrayApp initialization failed: {tray_init_error}")
            raise

        # Setup signal handlers
        logger.info("Setting up signal handlers...")
        setup_signal_handlers(backend, tray_app)
        logger.info("Signal handlers set up successfully")

        # Step 8: Start tray app (BLOCKING - runs in main thread)
        logger.info("Starting tray application (main thread blocks here)...")
        logger.info("Application is now running. Check system tray for icon.")
        logger.info("Close via tray menu to shutdown gracefully.")

        try:
            tray_app.start()  # BLOCKS until user quits
            logger.info("tray_app.start() returned normally")
        except Exception as tray_start_error:
            logger.exception(f"FATAL: TrayApp start failed: {tray_start_error}")
            raise

        logger.info("Tray app exited - application shutting down")

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")

    except Exception as e:
        logger.exception("Fatal error in main()")

        # Show user-friendly error MessageBox with MB_TOPMOST
        error_msg = (
            f"DeskPulse encountered a fatal error:\n\n"
            f"{str(e)}\n\n"
            f"Please check logs at:\n"
            f"{get_log_dir()}"
        )

        ctypes.windll.user32.MessageBoxW(
            0,
            error_msg,
            "DeskPulse - Fatal Error",
            MB_OK | MB_ICONERROR | MB_TOPMOST
        )

        sys.exit(1)

    finally:
        # Step 9: Graceful shutdown (<2s target)
        shutdown_start = time.time()
        logger.info("Cleanup starting...")

        try:
            # Stop tray app
            if tray_app:
                logger.info("Stopping tray app...")
                tray_app.stop()

            # Stop backend thread
            if backend:
                logger.info("Stopping backend thread...")
                backend.stop()

            # Flush all log handlers
            for handler in logging.root.handlers:
                handler.flush()

            shutdown_duration = time.time() - shutdown_start
            logger.info(f"Cleanup complete in {shutdown_duration:.2f}s")

            if shutdown_duration > 2.0:
                logger.warning(f"Shutdown exceeded 2s target: {shutdown_duration:.2f}s")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        finally:
            # Release mutex
            if mutex:
                try:
                    win32api.CloseHandle(mutex)
                    logger.debug("Mutex released")
                except:
                    pass


if __name__ == '__main__':
    main()
