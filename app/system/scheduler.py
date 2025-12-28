"""Background scheduler for DeskPulse daily tasks.

Manages scheduled tasks like end-of-day summaries using the `schedule` library.
Runs in dedicated daemon thread to avoid blocking main application.

CRITICAL: All scheduled tasks require Flask app context.

Story 4.6: End-of-Day Summary Report
"""

import schedule
import time
import threading
import logging
import atexit
from datetime import datetime

logger = logging.getLogger('deskpulse.system')


class DailyScheduler:
    """Background scheduler for daily tasks (end-of-day summary, updates).

    Uses `schedule` library (lightweight cron alternative) with dedicated
    daemon thread for non-blocking execution.

    Thread Safety:
        - Daemon thread: Automatically terminates when main process exits
        - GIL protection: schedule library is thread-safe for task registration
        - Flask app context: Direct app instance (self.app) passed at init,
          used within app.app_context() for database access

    Story 4.6: End-of-Day Summary Report
    """

    def __init__(self, app):
        """Initialize scheduler with Flask app context.

        Args:
            app: Flask app instance (NOT current_app proxy)
        """
        self.app = app
        self.running = False
        self.thread = None
        self.schedule = schedule

    def start(self):
        """Start scheduler daemon thread.

        Schedules daily tasks and begins background polling loop.
        Safe to call multiple times (idempotent).

        Returns:
            bool: True if started successfully
        """
        if self.running:
            logger.warning("Scheduler already running")
            return False

        # Schedule daily summary (default 6 PM, configurable via config)
        summary_time = self.app.config.get('DAILY_SUMMARY_TIME', '18:00')

        # Validate time format (defensive programming)
        try:
            datetime.strptime(summary_time, '%H:%M')
        except ValueError:
            logger.error(
                f"Invalid DAILY_SUMMARY_TIME format: '{summary_time}', "
                f"expected HH:MM (e.g., '18:00'). Using default 18:00."
            )
            summary_time = '18:00'

        # Schedule daily summary task
        self.schedule.every().day.at(summary_time).do(self._run_daily_summary)

        logger.info(f"Scheduled daily summary at {summary_time}")

        # Start scheduler thread (daemon=True for auto-cleanup on exit)
        # NOTE: Daemon thread pattern matches CV pipeline (app/__init__.py:102-127)
        # Both use daemon=True for auto-cleanup, thread safety via app context preservation
        self.thread = threading.Thread(
            target=self._schedule_loop,
            daemon=True,  # Matches CV pipeline pattern ✅
            name='DailyScheduler'
        )
        self.running = True
        self.thread.start()

        logger.info("Daily scheduler started successfully")
        return True

    def stop(self):
        """Stop scheduler (graceful shutdown).

        Sets running flag to False, causing schedule loop to exit.
        Daemon thread will terminate automatically.
        """
        if not self.running:
            logger.debug("Scheduler not running")
            return

        self.running = False
        logger.info("Daily scheduler stopped")

    def _schedule_loop(self):
        """Background thread loop - polls schedule every 60 seconds.

        Runs pending tasks and sleeps between checks.
        Continues until self.running is False.
        """
        logger.info("Scheduler polling loop started")

        while self.running:
            try:
                self.schedule.run_pending()
                time.sleep(60)  # Check every minute (efficient for daily tasks)
            except Exception:
                # Catch-all to prevent thread death from unexpected errors
                logger.exception("Scheduler loop error (continuing...)")
                time.sleep(60)  # Continue after error

        logger.info("Scheduler polling loop exited")

    def _run_daily_summary(self):
        """Execute daily summary task within Flask app context.

        Called by schedule library at configured time (default 6 PM).
        Runs within app context to enable database access.
        """
        logger.info("Daily summary task triggered")

        try:
            # CRITICAL: Run within Flask app context for database access
            with self.app.app_context():
                from app.alerts.notifier import send_daily_summary
                result = send_daily_summary()

                logger.info(
                    f"Daily summary completed: "
                    f"desktop={result['desktop_sent']}, "
                    f"socketio={result['socketio_sent']}"
                )
        except Exception:
            # Log exception but don't crash scheduler thread
            logger.exception("Daily summary task failed")


# Module-level singleton instance (initialized by create_app)
# Thread-safe: GIL protects singleton check, Flask app initialization is single-threaded
_scheduler_instance = None


def start_scheduler(app):
    """Start daily scheduler (called from create_app).

    Args:
        app: Flask app instance

    Returns:
        DailyScheduler: Scheduler instance (for testing/manual control)
    """
    global _scheduler_instance

    if _scheduler_instance is not None and _scheduler_instance.running:
        logger.warning("Scheduler already initialized")
        return _scheduler_instance

    _scheduler_instance = DailyScheduler(app)
    _scheduler_instance.start()

    return _scheduler_instance


def stop_scheduler():
    """Stop daily scheduler (called on app shutdown)."""
    global _scheduler_instance

    if _scheduler_instance is not None:
        _scheduler_instance.stop()


# Register graceful shutdown handler (enterprise requirement)
# Ensures scheduler stops cleanly when process exits
atexit.register(stop_scheduler)
