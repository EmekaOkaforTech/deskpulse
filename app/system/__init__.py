"""System integration module for DeskPulse.

Provides systemd integration including watchdog and readiness notifications.
"""

from app.system.watchdog import watchdog, WatchdogManager, get_notifier

__all__ = ["watchdog", "WatchdogManager", "get_notifier"]
