"""
Backend Thread Wrapper for Standalone Windows Edition.

Runs Flask backend in background thread without SocketIO.
Uses Windows camera and %APPDATA% paths.
"""

import threading
import logging
import time
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger('deskpulse.standalone.backend')


class BackendThread:
    """
    Flask backend running in background thread.

    Manages:
    - Flask app initialization
    - CV pipeline with Windows camera
    - Alert manager
    - Analytics engine
    - Graceful shutdown
    """

    def __init__(self, config: dict):
        """
        Initialize backend thread.

        Args:
            config: Configuration dictionary from config.py
        """
        self.config = config
        self.thread = None
        self.running = False
        self.flask_app = None
        self.cv_pipeline = None

        logger.info("BackendThread initialized")

    def start(self):
        """Start backend in background thread."""
        if self.running:
            logger.warning("Backend already running")
            return

        self.running = True
        self.thread = threading.Thread(
            target=self._run_backend,
            daemon=True,
            name='BackendThread'
        )
        self.thread.start()

        logger.info("Backend thread started")

    def _run_backend(self):
        """
        Backend main loop (runs in background thread).

        Initializes Flask app and CV pipeline, then runs monitoring loop.
        """
        try:
            logger.info("Backend thread running")

            # Import here to avoid circular imports
            from app.standalone.config import get_database_path
            from app import create_app
            from app.cv.pipeline import CVPipeline
            from app.standalone.camera_windows import WindowsCamera

            # Create Flask app with Windows config (standalone mode)
            database_path = str(get_database_path())
            self.flask_app = create_app(
                config_name='standalone',
                database_path=database_path,
                standalone_mode=True  # Skip SocketIO, Talisman, scheduler
            )

            # Initialize database
            with self.flask_app.app_context():
                from app.extensions import init_db
                init_db()
                logger.info(f"Database initialized: {database_path}")

            # Create Windows camera
            camera_config = self.config.get('camera', {})
            camera = WindowsCamera(
                camera_index=camera_config.get('index', 0),
                fps=camera_config.get('fps', 10),
                width=camera_config.get('width', 640),
                height=camera_config.get('height', 480)
            )

            if not camera.open():
                logger.error("Failed to open camera, backend stopping")
                self.running = False
                return

            # Create CV pipeline with Windows camera
            self.cv_pipeline = CVPipeline(
                camera=camera,
                app=self.flask_app
            )

            # Start CV pipeline
            self.cv_pipeline.start()
            logger.info("CV pipeline started")

            # Main loop - keep thread alive
            while self.running:
                time.sleep(1)

                # Health check
                if not self.cv_pipeline.is_running():
                    logger.warning("CV pipeline stopped unexpectedly")
                    # Could restart or notify user

            logger.info("Backend thread stopping")

        except Exception as e:
            logger.exception(f"Backend thread error: {e}")
            self.running = False

        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup resources."""
        try:
            if self.cv_pipeline:
                self.cv_pipeline.stop()
                logger.info("CV pipeline stopped")

            if self.flask_app:
                # Cleanup Flask resources
                logger.info("Flask app cleanup")

        except Exception as e:
            logger.exception(f"Cleanup error: {e}")

    def stop(self):
        """Stop backend gracefully."""
        if not self.running:
            logger.warning("Backend not running")
            return

        logger.info("Stopping backend...")
        self.running = False

        # Wait for thread to finish (max 5 seconds)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        logger.info("Backend stopped")

    def is_running(self) -> bool:
        """Check if backend is running."""
        return self.running and self.thread is not None and self.thread.is_alive()

    def get_status(self) -> dict:
        """
        Get backend status.

        Returns:
            dict: Status information
        """
        status = {
            'running': self.is_running(),
            'pipeline_active': False,
            'camera_connected': False,
            'monitoring_active': False
        }

        if self.cv_pipeline:
            status['pipeline_active'] = self.cv_pipeline.is_running()

            if self.cv_pipeline.camera:
                status['camera_connected'] = self.cv_pipeline.camera.is_available()

            if self.cv_pipeline.alert_manager:
                status['monitoring_active'] = self.cv_pipeline.alert_manager.get_monitoring_status().get('monitoring_active', False)

        return status

    def pause_monitoring(self):
        """Pause posture monitoring."""
        if self.cv_pipeline and self.cv_pipeline.alert_manager:
            self.cv_pipeline.alert_manager.pause_monitoring()
            logger.info("Monitoring paused")

    def resume_monitoring(self):
        """Resume posture monitoring."""
        if self.cv_pipeline and self.cv_pipeline.alert_manager:
            self.cv_pipeline.alert_manager.resume_monitoring()
            logger.info("Monitoring resumed")

    def get_today_stats(self) -> Optional[dict]:
        """
        Get today's posture statistics.

        Returns:
            dict: Today's stats or None if not available
        """
        if not self.flask_app:
            return None

        try:
            with self.flask_app.app_context():
                from app.data.analytics import get_today_stats
                return get_today_stats()

        except Exception as e:
            logger.exception(f"Error getting stats: {e}")
            return None

    def get_history(self, days: int = 7) -> Optional[list]:
        """
        Get posture history.

        Args:
            days: Number of days of history

        Returns:
            list: History data or None if not available
        """
        if not self.flask_app:
            return None

        try:
            with self.flask_app.app_context():
                from app.data.analytics import get_daily_stats
                return get_daily_stats(days=days)

        except Exception as e:
            logger.exception(f"Error getting history: {e}")
            return None


# Global backend instance (singleton)
_backend_instance: Optional[BackendThread] = None
_backend_lock = threading.Lock()


def get_backend() -> Optional[BackendThread]:
    """
    Get global backend instance.

    Returns:
        BackendThread: Global backend instance or None
    """
    return _backend_instance


def start_backend(config: dict) -> BackendThread:
    """
    Start backend (singleton pattern).

    Args:
        config: Configuration dictionary

    Returns:
        BackendThread: Global backend instance
    """
    global _backend_instance

    with _backend_lock:
        if _backend_instance is not None:
            logger.warning("Backend already started")
            return _backend_instance

        _backend_instance = BackendThread(config)
        _backend_instance.start()

        # Wait for backend to initialize
        time.sleep(2)

        return _backend_instance


def stop_backend():
    """Stop global backend instance."""
    global _backend_instance

    with _backend_lock:
        if _backend_instance is None:
            logger.warning("Backend not started")
            return

        _backend_instance.stop()
        _backend_instance = None


if __name__ == '__main__':
    # Test backend thread
    from app.standalone.config import setup_logging, load_config

    setup_logging()

    print("DeskPulse Backend Thread Test")
    print("=" * 50)

    config = load_config()

    print("\n1. Starting backend...")
    backend = start_backend(config)

    print("2. Backend running, waiting 10 seconds...")
    time.sleep(10)

    print("\n3. Getting status...")
    status = backend.get_status()
    print(f"Status: {status}")

    print("\n4. Getting today's stats...")
    stats = backend.get_today_stats()
    if stats:
        print(f"Stats: {stats}")
    else:
        print("No stats available yet")

    print("\n5. Stopping backend...")
    stop_backend()

    print("\n" + "=" * 50)
    print("Test complete!")
