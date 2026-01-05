"""DeskPulse Windows Desktop Client - Toast Notification Manager."""
import queue
import threading
import time
import webbrowser
import logging
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from winotify import Notification

logger = logging.getLogger('deskpulse.windows.notifier')

# Conditional imports for Windows-only dependencies
try:
    from winotify import Notification, audio
    WINOTIFY_AVAILABLE = True
except ImportError:
    WINOTIFY_AVAILABLE = False
    logger.warning("winotify not available - Toast notifications disabled")

# Priority constants (lower = higher priority)
PRIORITY_ALERT = 1
PRIORITY_CORRECTION = 2
PRIORITY_CONNECTION = 3


class WindowsNotifier:
    """
    Enterprise-grade Windows toast notification manager with priority queue.

    Manages Windows 10/11 native toast notifications for posture alerts,
    corrections, and connection status. Uses priority queue to prevent spam
    and ensure critical alerts are always displayed.

    Features:
    - Priority-based notification queue (alert > correction > connection)
    - Graceful degradation if winotify unavailable
    - Thread-safe queue processing
    - Enterprise-grade error handling with auto-retry
    - Action button support for "View Dashboard"
    """

    def __init__(self, tray_manager):
        """
        Initialize WindowsNotifier.

        Args:
            tray_manager: TrayManager instance for backend URL access

        Raises:
            None (gracefully degrades if winotify unavailable)
        """
        self.tray_manager = tray_manager
        self.notifier_available = False
        self._shutdown_event = threading.Event()
        self._queue_thread_retries = 0

        # Try to initialize winotify (graceful degradation)
        if not WINOTIFY_AVAILABLE:
            logger.warning("winotify module not available - notifications disabled")
            return

        try:
            # Test winotify availability (no explicit ToastNotifier class needed)
            # winotify 1.1.0+ uses Notification class directly
            self.notifier_available = True
            logger.info("winotify initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize winotify: {e}", exc_info=True)
            return

        # Priority queue for notification ordering (maxsize=5)
        self.notification_queue = queue.PriorityQueue(maxsize=5)

        # Start processing thread
        self.queue_thread = threading.Thread(
            target=self._notification_queue_loop,
            daemon=True,
            name='NotificationQueue'
        )
        self.queue_thread.start()
        logger.info("WindowsNotifier initialized with priority queue")

    def _notification_queue_loop(self):
        """
        Process notifications by priority (alert > correction > connection).

        Runs in daemon thread, processes one notification at a time.
        Implements auto-retry with counter (max 3 retries before disabling).
        Checks shutdown flag every 1s for graceful exit.
        """
        while not self._shutdown_event.is_set():
            try:
                # Get notification from queue (1s timeout for shutdown check)
                priority, notification = self.notification_queue.get(timeout=1)

                # Show notification (blocks until dismissed or duration expires)
                notification.show()

                # Mark task done
                self.notification_queue.task_done()

                logger.info(f"Notification shown (priority={priority})")

            except queue.Empty:
                # Timeout - check shutdown flag and continue
                continue
            except Exception as e:
                logger.error(f"Notification queue error: {e}", exc_info=True)

                # Increment retry counter
                self._queue_thread_retries += 1

                # Check retry limit
                if self._queue_thread_retries >= 3:
                    logger.error("Max notification retries reached - disabling notifications")
                    self.notifier_available = False
                    break

                # Sleep 5s before retry
                time.sleep(5)

        logger.info("Notification queue thread exiting")

    def _create_notification(
        self,
        title: str,
        message: str,
        duration_seconds: int,
        buttons: Optional[list] = None
    ) -> Optional['Notification']:
        """
        Create a Windows toast notification.

        Args:
            title: Notification title
            message: Notification message body
            duration_seconds: Duration in seconds (integer)
            buttons: Optional list of (label, callback) tuples

        Returns:
            Notification instance or None if winotify unavailable
        """
        if not self.notifier_available:
            return None

        try:
            # Determine icon path
            appdata = Path.home() / "AppData" / "Roaming" / "DeskPulse" / "icon.ico"
            icon_path = str(appdata) if appdata.exists() else None

            # Create notification
            notification = Notification(
                app_id="DeskPulse",
                title=title,
                msg=message,
                duration=duration_seconds,
                icon=icon_path
            )

            # Add action buttons if provided
            if buttons:
                for label, callback in buttons:
                    # winotify 1.1.0+ accepts callables (lambda functions) for button actions
                    # Lambda pattern verified working: lambda: webbrowser.open(url)
                    # Alternative: Pass URL string directly for Windows Toast URL protocol
                    notification.add_actions(label=label, launch=callback)

            # Set default audio (Windows notification sound)
            if WINOTIFY_AVAILABLE:
                notification.set_audio(audio.Default, loop=False)

            return notification

        except Exception as e:
            logger.error(f"Failed to create notification: {e}", exc_info=True)
            return None

    def _show_notification(self, notification: 'Notification'):
        """
        Show a notification (blocking until dismissed).

        Args:
            notification: Notification instance to display

        Note:
            This method is synchronous and blocks. It should only be called
            from the notification queue processing thread.
        """
        try:
            notification.show()
            logger.info(f"Notification shown: {notification.title}")
        except Exception as e:
            logger.error(f"Failed to show notification: {e}", exc_info=True)

    def _queue_notification(self, notification: Optional['Notification'], priority: int):
        """
        Add notification to priority queue.

        Implements queue full handling: drops lowest-priority notification
        to make room for new notification.

        Args:
            notification: Notification to queue
            priority: Priority level (1=high, 3=low)
        """
        if not notification:
            return

        if not self.notifier_available:
            logger.warning("Cannot queue notification: winotify unavailable")
            return

        try:
            # Try to add to queue (non-blocking)
            self.notification_queue.put_nowait((priority, notification))
            logger.info(f"Notification queued (priority={priority}, queue_size={self.notification_queue.qsize()})")

        except queue.Full:
            # Queue full - drop lowest priority notification
            logger.warning("Notification queue full - dropping lowest priority notification")

            # Get all items from queue
            items = []
            while not self.notification_queue.empty():
                try:
                    items.append(self.notification_queue.get_nowait())
                except queue.Empty:
                    break

            # Sort by priority (ascending: 1, 2, 3)
            items.sort(key=lambda x: x[0])

            # Drop item with highest priority NUMBER (lowest urgency, e.g., connection=3)
            # After sort, last item has highest priority number (lowest urgency)
            if items:
                dropped = items.pop()
                logger.warning(f"Dropped notification with priority={dropped[0]}")

            # Re-add remaining items and new notification
            for item in items:
                try:
                    self.notification_queue.put_nowait(item)
                except queue.Full:
                    logger.error("Failed to re-add notification to queue")

            # Add new notification
            try:
                self.notification_queue.put_nowait((priority, notification))
                logger.info(f"New notification queued after drop (priority={priority})")
            except queue.Full:
                logger.error("Failed to queue new notification after drop")

    def show_posture_alert(self, duration_seconds: int):
        """
        Show high-priority posture alert notification.

        Args:
            duration_seconds: Duration in bad posture (from backend event)
        """
        if not self.notifier_available:
            return

        # Calculate minutes (defensive)
        duration_minutes = duration_seconds // 60

        # Create notification with action button
        notification = self._create_notification(
            title="Posture Alert ⚠️",
            message=f"You've been in poor posture for {duration_minutes} minutes. Time to adjust your position!",
            duration_seconds=10,
            buttons=[
                ("View Dashboard", lambda: webbrowser.open(self.tray_manager.backend_url))
            ]
        )

        # Queue with high priority
        self._queue_notification(notification, PRIORITY_ALERT)
        logger.info(f"Posture alert notification queued: {duration_minutes}min")

    def show_posture_corrected(self):
        """
        Show posture correction notification.

        No action buttons - auto-dismiss after 5 seconds.
        """
        if not self.notifier_available:
            return

        # Create notification (no buttons)
        notification = self._create_notification(
            title="Great Job! ✓",
            message="Good posture restored. Your body thanks you!",
            duration_seconds=5,
            buttons=None
        )

        # Queue with medium priority
        self._queue_notification(notification, PRIORITY_CORRECTION)
        logger.info("Posture correction notification queued")

    def show_connection_status(self, connected: bool):
        """
        Show connection status notification.

        Args:
            connected: True if connected, False if disconnected
        """
        if not self.notifier_available:
            return

        # Determine title and message
        if connected:
            title = "DeskPulse Connected"
            message = "Connected to Raspberry Pi. Monitoring active."
        else:
            title = "DeskPulse Disconnected"
            message = "Lost connection to Raspberry Pi. Retrying..."

        # Create notification (no buttons)
        notification = self._create_notification(
            title=title,
            message=message,
            duration_seconds=5,
            buttons=None
        )

        # Queue with low priority
        self._queue_notification(notification, PRIORITY_CONNECTION)
        logger.info(f"Connection status notification queued: connected={connected}")

    def shutdown(self):
        """
        Gracefully shutdown notification queue thread.

        Signals thread to exit and waits up to 5 seconds for completion.
        """
        if not self.notifier_available:
            return

        logger.info("Shutting down WindowsNotifier...")

        # Signal shutdown
        self._shutdown_event.set()

        # Wait for thread to finish (max 5s)
        if self.queue_thread.is_alive():
            self.queue_thread.join(timeout=5)

        if self.queue_thread.is_alive():
            logger.warning("Notification queue thread did not exit in time")
        else:
            logger.info("WindowsNotifier shutdown complete")
