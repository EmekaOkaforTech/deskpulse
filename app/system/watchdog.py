"""systemd watchdog integration module.

Provides systemd readiness notification and watchdog pinging for DeskPulse.
Gracefully degrades when not running under systemd or when sdnotify is unavailable.
"""

import logging
import os
import threading

# Hierarchical logger for system operations (AC2)
logger = logging.getLogger("deskpulse.system")

# Graceful sdnotify import - may not be available in all environments
try:
    import sdnotify

    SDNOTIFY_AVAILABLE = True
except ImportError:
    SDNOTIFY_AVAILABLE = False
    sdnotify = None


def get_notifier():
    """Get systemd notifier if running under systemd.

    Returns:
        SystemdNotifier instance if under systemd, None otherwise.
    """
    if not os.environ.get("NOTIFY_SOCKET"):
        return None
    if not SDNOTIFY_AVAILABLE:
        return None
    try:
        return sdnotify.SystemdNotifier()
    except Exception:
        return None


class WatchdogManager:
    """Manages systemd watchdog pings.

    Sends periodic WATCHDOG=1 notifications to systemd to prove liveness.
    When systemd doesn't receive a ping within WatchdogSec, it restarts
    the service.

    Attributes:
        interval: Seconds between watchdog pings (must be < WatchdogSec/2).
        notifier: SystemdNotifier instance or None if not under systemd.

    Example:
        watchdog = WatchdogManager()
        watchdog.start()  # Start background ping thread
        # ... application runs ...
        watchdog.stop()   # Clean shutdown
    """

    def __init__(self):
        """Initialize WatchdogManager."""
        self.notifier = None
        self.interval = 14  # seconds (must be < WatchdogSec/2 = 30/2 = 15)
        self._stop_event = threading.Event()
        self._thread = None

        # Only create notifier if running under systemd
        if os.environ.get("NOTIFY_SOCKET"):
            if SDNOTIFY_AVAILABLE:
                try:
                    self.notifier = sdnotify.SystemdNotifier()
                except Exception:
                    self.notifier = None

    def start(self):
        """Start the watchdog ping thread.

        Spawns a daemon thread that sends periodic WATCHDOG=1 pings.
        No-op if not running under systemd.
        """
        if self.notifier:
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._ping_loop, daemon=True, name="watchdog-ping"
            )
            self._thread.start()
            logger.debug("Watchdog ping thread started: interval=%ds", self.interval)

    def stop(self):
        """Stop the watchdog ping thread.

        Signals the ping thread to stop and waits for it to terminate.
        """
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            logger.debug("Watchdog ping thread stopped")

    def _ping_loop(self):
        """Send periodic WATCHDOG=1 pings to systemd."""
        while not self._stop_event.is_set():
            if self.notifier:
                try:
                    self.notifier.notify("WATCHDOG=1")
                    logger.debug("Watchdog ping sent")
                except Exception:
                    pass
            self._stop_event.wait(self.interval)

    def ping(self):
        """Send immediate watchdog ping.

        Can be called from main processing loop for additional health checks.
        No-op if not running under systemd.
        """
        if self.notifier:
            try:
                self.notifier.notify("WATCHDOG=1")
            except Exception:
                pass

    def notify_ready(self):
        """Send READY=1 notification to systemd.

        Should be called after application initialization is complete.
        """
        if self.notifier:
            try:
                self.notifier.notify("READY=1")
                logger.info("systemd READY notification sent")
            except Exception:
                pass

    def notify_status(self, status):
        """Send status update to systemd.

        Args:
            status: Human-readable status string (visible in systemctl status).
        """
        if self.notifier:
            try:
                self.notifier.notify(f"STATUS={status}")
            except Exception:
                pass

    def notify_stopping(self):
        """Send STOPPING=1 notification to systemd.

        Should be called when application is shutting down gracefully.
        """
        if self.notifier:
            try:
                self.notifier.notify("STOPPING=1")
                logger.info("systemd STOPPING notification sent")
            except Exception:
                pass


# Global watchdog instance for application-wide use
watchdog = WatchdogManager()
