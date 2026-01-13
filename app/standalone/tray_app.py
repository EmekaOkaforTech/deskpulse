"""
DeskPulse Standalone Tray Application (Story 8.4).

System tray manager using LOCAL IPC (event queue + direct backend calls).
NO network SocketIO - all communication via in-process callbacks and queue.

Architecture:
- Event queue consumer thread (processes backend events)
- Direct backend method calls (pause/resume/get_stats)
- Toast notifications via winotify
- System tray icon with pystray
"""

import logging
import threading
import queue
import time
from typing import Optional
from datetime import datetime
import ctypes

logger = logging.getLogger('deskpulse.standalone.tray')

# Windows MessageBox helper that works from any thread
def show_message_box(title: str, message: str, style: int = 0) -> int:
    """
    Show Windows MessageBox that works from background threads.

    Uses MB_SYSTEMMODAL to ensure dialog works even when called from
    non-GUI threads (like tray menu callbacks).

    Args:
        title: Dialog title
        message: Dialog message
        style: MB_* flags (MB_OK, MB_YESNO, etc.)

    Returns:
        int: Dialog result (IDOK=1, IDCANCEL=2, IDYES=6, IDNO=7)
    """
    # MB_SYSTEMMODAL (0x1000) ensures dialog is interactive from any thread
    # MB_SETFOREGROUND (0x10000) brings dialog to front
    flags = style | 0x1000 | 0x10000  # MB_SYSTEMMODAL | MB_SETFOREGROUND

    return ctypes.windll.user32.MessageBoxW(0, message, title, flags)

# Conditional imports for Windows dependencies
try:
    import pystray
    from PIL import Image, ImageDraw
    from winotify import Notification, audio
    WINDOWS_AVAILABLE = True
except ImportError:
    pystray = None  # type: ignore
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    Notification = None  # type: ignore
    audio = None  # type: ignore
    WINDOWS_AVAILABLE = False
    logger.warning("pystray/Pillow/winotify not available - Windows features disabled")

# Import priority constants
from app.standalone.backend_thread import (
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    PRIORITY_LOW
)

# Icon state colors (enterprise teal theme)
STATE_COLORS = {
    'monitoring': (0, 139, 139, 255),    # Teal: Monitoring active
    'paused': (128, 128, 128, 255),      # Gray: Monitoring paused
    'alert': (200, 0, 0, 255),           # Red: Alert active
    'disconnected': (100, 100, 100, 255) # Dark gray: Backend not running
}


class TrayApp:
    """
    System tray application for standalone DeskPulse.

    ENTERPRISE: Event queue consumer with graceful shutdown,
    priority-based processing, and comprehensive error handling.

    Architecture:
    - Main thread: pystray icon (blocking run loop)
    - Consumer thread: Event queue consumer (daemon)
    - Backend thread: Managed by BackendThread class
    """

    def __init__(self, backend_thread, event_queue: queue.PriorityQueue):
        """
        Initialize tray application.

        Args:
            backend_thread: BackendThread instance (for direct method calls)
            event_queue: Priority queue for backend events
        """
        if not WINDOWS_AVAILABLE:
            raise ImportError("pystray, Pillow, and winotify are required for TrayApp")

        self.backend = backend_thread
        self.event_queue = event_queue

        # Application state
        self.monitoring_active = True  # Synced from backend
        self.alert_active = False      # True when alert notification shown
        self.running = False

        # Threading
        self.consumer_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()

        # Event processing metrics (Story 8.4 - Task 3.5)
        self._events_processed = 0
        self._latency_samples = []  # Keep last 100 for p95
        self._metrics_lock = threading.Lock()
        self._last_metrics_log = time.time()

        # Tray icon
        self.icon_cache = {}
        self._create_icon_images()
        self.icon: Optional[pystray.Icon] = None

        logger.info("TrayApp initialized")

    def _create_icon_images(self):
        """Create tray icon images for each state."""
        # 32x32 icons with simple colored circle
        size = (32, 32)

        for state, color in STATE_COLORS.items():
            image = Image.new('RGBA', size, (255, 255, 255, 0))  # Transparent background
            draw = ImageDraw.Draw(image)
            # Draw filled circle
            draw.ellipse([4, 4, 28, 28], fill=color, outline=(0, 0, 0, 255))
            self.icon_cache[state] = image

        logger.debug(f"Created {len(self.icon_cache)} icon images")

    def start(self):
        """
        Start tray application.

        Starts event queue consumer thread and tray icon.
        Blocks until icon.stop() called.
        """
        if self.running:
            logger.warning("TrayApp already running")
            return

        self.running = True

        # Start event queue consumer thread
        self.consumer_thread = threading.Thread(
            target=self._event_consumer_loop,
            daemon=True,  # Daemon thread for clean shutdown
            name='EventConsumer'
        )
        self.consumer_thread.start()
        logger.info("Event consumer thread started")

        # Create and run tray icon (blocking)
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "Pause Monitoring" if self.monitoring_active else "Resume Monitoring",
                self._toggle_monitoring
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("View Camera Feed", self._show_camera_preview),
            pystray.MenuItem("Today's Stats", self._show_stats),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._show_settings),
            pystray.MenuItem("About", self._show_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit DeskPulse", self._quit_app)
        )

        self.icon = pystray.Icon(
            "DeskPulse",
            self.icon_cache['monitoring'],
            "DeskPulse - Monitoring Active",
            menu
        )

        logger.info("Starting tray icon (blocking)...")
        self.icon.run()  # Blocks until icon.stop() called

    def stop(self):
        """
        Stop tray application gracefully.

        Enterprise shutdown sequence:
        1. Set shutdown flag
        2. Drain event queue (2 sec timeout)
        3. Join consumer thread (5 sec timeout)
        4. Stop tray icon
        """
        if not self.running:
            logger.warning("TrayApp not running")
            return

        logger.info("Stopping TrayApp...")
        self.running = False
        self.shutdown_event.set()

        # Wait for event queue to drain (2 sec timeout)
        try:
            # Note: join() waits for all tasks to be marked done
            # This ensures no events are lost during shutdown
            logger.info("Waiting for event queue to drain...")
            # Can't use queue.join() with PriorityQueue directly
            # Just give consumer time to process remaining events
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Queue drain error: {e}")

        # Join consumer thread (5 sec timeout)
        if self.consumer_thread and self.consumer_thread.is_alive():
            logger.info("Joining consumer thread...")
            self.consumer_thread.join(timeout=5)
            if self.consumer_thread.is_alive():
                logger.warning("Consumer thread still alive after 5s timeout")

        # Stop tray icon (if running)
        if self.icon:
            self.icon.stop()

        logger.info("TrayApp stopped")

    def _event_consumer_loop(self):
        """
        Event queue consumer loop.

        ENTERPRISE: Graceful shutdown, priority processing, latency tracking,
        comprehensive error handling, metrics logging.
        """
        logger.info("Event consumer loop started")

        while self.running:
            try:
                # Check shutdown signal before blocking on queue
                if self.shutdown_event.is_set():
                    logger.info("Shutdown signal received, draining queue...")
                    break

                # Get event from priority queue (100ms timeout for shutdown responsiveness)
                try:
                    event = self.event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue  # No events, loop again

                # Unpack event: (priority, enqueue_timestamp, event_type, data)
                priority, enqueue_time, event_type, data = event

                # Calculate latency (enqueue to dequeue)
                dequeue_time = time.perf_counter()
                latency_ms = (dequeue_time - enqueue_time) * 1000

                # Track latency sample
                with self._metrics_lock:
                    self._latency_samples.append(latency_ms)
                    if len(self._latency_samples) > 100:
                        self._latency_samples.pop(0)  # Keep last 100

                # Process event
                self._handle_event(event_type, data, latency_ms)

                # Mark task done (for queue.join() if we add it later)
                self.event_queue.task_done()

                # Increment processed counter
                with self._metrics_lock:
                    self._events_processed += 1

                # Log metrics every 60 seconds
                self._log_metrics_if_due()

            except Exception as e:
                logger.exception(f"Event consumer loop error: {e}")
                # Continue processing (don't crash consumer thread)

        logger.info("Event consumer loop exited")

    def _handle_event(self, event_type: str, data: dict, latency_ms: float):
        """
        Handle event based on type.

        Args:
            event_type: Event type string
            data: Event data dictionary
            latency_ms: Event latency in milliseconds
        """
        try:
            if event_type == 'alert':
                self._handle_alert(data, latency_ms)
            elif event_type == 'correction':
                self._handle_correction(data, latency_ms)
            elif event_type == 'status_change':
                self._handle_status_change(data)
            elif event_type == 'camera_state':
                self._handle_camera_state(data)
            elif event_type == 'error':
                self._handle_error(data)
            else:
                logger.debug(f"Unhandled event type: {event_type}")

        except Exception as e:
            logger.exception(f"Error handling event '{event_type}': {e}")

    def _handle_alert(self, data: dict, latency_ms: float):
        """
        Handle alert event.

        Shows toast notification and updates tray icon to red.

        Args:
            data: Alert data (duration, timestamp)
            latency_ms: Event latency in milliseconds
        """
        duration = data.get('duration', 0)
        minutes = duration // 60

        logger.warning(f"ALERT: Bad posture for {minutes} minutes (latency: {latency_ms:.1f}ms)")

        # Update tray icon to alert state
        self.alert_active = True
        self._update_tray_icon()

        # Show toast notification
        self._show_toast(
            title="⚠️ Posture Alert",
            message=f"Bad posture detected for {minutes} minutes. Please adjust your posture!",
            duration="long",
            sound=audio.IM
        )

        # Log if latency exceeds target
        if latency_ms > 50:
            logger.warning(f"Alert latency {latency_ms:.1f}ms exceeds 50ms target")

    def _handle_correction(self, data: dict, latency_ms: float):
        """
        Handle correction event.

        Shows positive toast notification.

        Args:
            data: Correction data (previous_duration, timestamp)
            latency_ms: Event latency in milliseconds
        """
        previous_duration = data.get('previous_duration', 0)
        minutes = previous_duration // 60

        logger.info(f"CORRECTION: Good posture restored (was bad for {minutes} min, latency: {latency_ms:.1f}ms)")

        # Clear alert state
        self.alert_active = False
        self._update_tray_icon()

        # Show positive toast
        self._show_toast(
            title="✓ Posture Corrected",
            message=f"Great job! You've corrected your posture after {minutes} minutes.",
            duration="short",
            sound=audio.Default
        )

    def _handle_status_change(self, data: dict):
        """
        Handle monitoring status change event.

        Updates internal state and tray icon.

        Args:
            data: Status data (monitoring_active, threshold_seconds)
        """
        self.monitoring_active = data.get('monitoring_active', False)
        threshold = data.get('threshold_seconds', 600)

        logger.info(f"Status change: monitoring_active={self.monitoring_active}, threshold={threshold}s")

        # Update tray icon
        self._update_tray_icon()

    def _handle_camera_state(self, data: dict):
        """
        Handle camera state change event.

        Args:
            data: Camera state data (state, timestamp)
        """
        state = data.get('state', 'unknown')
        logger.info(f"Camera state: {state}")

        # Could show notification if camera disconnects
        # For now, just log

    def _handle_error(self, data: dict):
        """
        Handle error event.

        Shows error toast notification.

        Args:
            data: Error data (message, error_type)
        """
        message = data.get('message', 'Unknown error')
        error_type = data.get('error_type', 'general')

        logger.error(f"Backend error [{error_type}]: {message}")

        # Show error toast
        self._show_toast(
            title=f"⚠️ Error: {error_type}",
            message=message,
            duration="long",
            sound=audio.Default
        )

    def _show_toast(self, title: str, message: str, duration: str = "short", sound=None):
        """
        Show Windows toast notification.

        Args:
            title: Notification title
            message: Notification message
            duration: "short" or "long"
            sound: winotify.audio constant
        """
        try:
            toast = Notification(
                app_id="DeskPulse",
                title=title,
                msg=message,
                duration=duration
            )

            if sound:
                toast.set_audio(sound, loop=False)

            toast.show()

        except Exception as e:
            logger.exception(f"Toast notification error: {e}")

    def _update_tray_icon(self):
        """Update tray icon based on current state."""
        if not self.icon:
            return

        # Determine icon state
        if self.alert_active:
            state = 'alert'
            tooltip = "DeskPulse - ALERT: Bad Posture Detected"
        elif not self.monitoring_active:
            state = 'paused'
            tooltip = "DeskPulse - Monitoring Paused"
        else:
            state = 'monitoring'
            tooltip = "DeskPulse - Monitoring Active"

        # Update icon
        self.icon.icon = self.icon_cache[state]
        self.icon.title = tooltip

    def _toggle_monitoring(self):
        """Toggle monitoring (pause/resume) via menu."""
        try:
            if self.monitoring_active:
                # Pause monitoring
                self.backend.pause_monitoring()
                logger.info("Monitoring paused via tray menu")
            else:
                # Resume monitoring
                self.backend.resume_monitoring()
                logger.info("Monitoring resumed via tray menu")

            # State will be updated via status_change event
            # Force menu refresh to update text immediately
            if self.icon:
                self.icon.update_menu()

        except Exception as e:
            logger.exception(f"Toggle monitoring error: {e}")
            self._show_toast(
                title="⚠️ Error",
                message=f"Failed to toggle monitoring: {e}",
                duration="short"
            )

    def _show_camera_preview(self):
        """
        Show camera feed preview window with pose landmarks.

        Opens a non-blocking OpenCV window showing the camera feed.
        Press 'q' or ESC to close the preview.
        """
        try:
            import cv2
            import threading

            def preview_thread():
                """Run camera preview in separate thread to avoid blocking tray."""
                try:
                    # Get camera from backend
                    if not hasattr(self.backend, 'camera') or not self.backend.camera:
                        logger.warning("Camera not available for preview")
                        self._show_toast(
                            title="Camera Preview",
                            message="Camera is not initialized. Please ensure monitoring is active.",
                            duration="short"
                        )
                        return

                    logger.info("Starting camera preview window")

                    # Create window
                    window_name = "DeskPulse - Camera Preview (Press Q or ESC to close)"
                    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                    cv2.resizeWindow(window_name, 640, 480)

                    # Preview loop
                    while True:
                        # Get frame from camera (returns tuple: success, frame)
                        success, frame = self.backend.camera.read()

                        if not success or frame is None:
                            logger.warning("Failed to read frame from camera")
                            break

                        # Get latest landmarks from CV pipeline for skeleton overlay
                        landmarks = None
                        posture_state = None
                        if hasattr(self.backend, 'cv_pipeline') and self.backend.cv_pipeline:
                            if hasattr(self.backend.cv_pipeline, 'detector'):
                                try:
                                    # Detect landmarks on this frame
                                    detection_result = self.backend.cv_pipeline.detector.detect_landmarks(frame)
                                    landmarks = detection_result.get('landmarks')

                                    # Get posture state for color
                                    if landmarks and hasattr(self.backend.cv_pipeline, 'classifier'):
                                        posture_state = self.backend.cv_pipeline.classifier.classify_posture(landmarks)
                                except:
                                    pass

                        # Draw skeleton overlay if landmarks available
                        if landmarks:
                            # Determine skeleton color based on posture
                            if posture_state == 'good':
                                skeleton_color = (0, 255, 0)  # Green
                            elif posture_state == 'bad':
                                skeleton_color = (0, 0, 255)  # Red
                            else:
                                skeleton_color = (255, 255, 0)  # Yellow (unknown)

                            # Draw landmarks manually (simplified - just key points)
                            h, w, _ = frame.shape
                            for i, lm in enumerate(landmarks):
                                # Draw landmark points
                                x = int(lm.x * w)
                                y = int(lm.y * h)
                                cv2.circle(frame, (x, y), 3, skeleton_color, -1)

                        # Check if monitoring is paused
                        monitoring_paused = False
                        if hasattr(self.backend, 'cv_pipeline') and self.backend.cv_pipeline:
                            if hasattr(self.backend.cv_pipeline, 'alert_manager') and self.backend.cv_pipeline.alert_manager:
                                monitoring_paused = self.backend.cv_pipeline.alert_manager.monitoring_paused

                        # Add monitoring status overlay
                        if monitoring_paused:
                            # Large "MONITORING PAUSED" text
                            cv2.putText(
                                frame,
                                "MONITORING PAUSED",
                                (10, 100),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                1.2,
                                (0, 165, 255),  # Orange
                                3
                            )

                        # Add text overlay
                        cv2.putText(
                            frame,
                            "DeskPulse Camera Feed",
                            (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2
                        )

                        cv2.putText(
                            frame,
                            "Press Q or ESC to close",
                            (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 255, 255),
                            1
                        )

                        # Show frame
                        cv2.imshow(window_name, frame)

                        # Check for key press (30ms delay = ~30 FPS)
                        key = cv2.waitKey(30) & 0xFF
                        if key == ord('q') or key == 27:  # 'q' or ESC
                            break

                        # Check if window was closed
                        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                            break

                    # Cleanup
                    cv2.destroyWindow(window_name)
                    logger.info("Camera preview window closed")

                except Exception as e:
                    logger.exception(f"Camera preview error: {e}")
                    self._show_toast(
                        title="⚠️ Preview Error",
                        message=f"Failed to show camera preview: {e}",
                        duration="short"
                    )

            # Start preview in background thread
            thread = threading.Thread(target=preview_thread, daemon=True, name='CameraPreview')
            thread.start()

        except Exception as e:
            logger.exception(f"Show camera preview error: {e}")
            self._show_toast(
                title="⚠️ Error",
                message=f"Failed to start camera preview: {e}",
                duration="short"
            )

    def _show_stats(self):
        """Show today's statistics via message box."""
        try:
            # Force fresh stats (bypass cache) for accurate display
            stats = None
            if self.backend.flask_app:
                try:
                    with self.backend.flask_app.app_context():
                        from app.data.analytics import PostureAnalytics
                        from datetime import date
                        stats = PostureAnalytics.calculate_daily_stats(date.today())
                except Exception as e:
                    logger.exception(f"Error fetching fresh stats: {e}")
                    # Fallback to cached stats
                    stats = self.backend.get_today_stats()

            if stats:
                # Format stats
                good_minutes = stats.get('good_duration_seconds', 0) // 60
                bad_minutes = stats.get('bad_duration_seconds', 0) // 60
                score = stats.get('posture_score', 0)

                message = f"""Today's Posture Statistics

Good Posture: {good_minutes} minutes
Bad Posture: {bad_minutes} minutes
Score: {score:.1f}%

Keep up the good work!"""
            else:
                message = "No statistics available yet.\n\nStart monitoring to track your posture!"

            # Show message box using thread-safe helper
            show_message_box(
                "DeskPulse Statistics",
                message,
                0x0 | 0x40  # MB_OK | MB_ICONINFORMATION
            )

        except Exception as e:
            logger.exception(f"Show stats error: {e}")
            self._show_toast(
                title="⚠️ Error",
                message=f"Failed to retrieve statistics: {e}",
                duration="short"
            )

    def _show_settings(self):
        """Show settings menu with config path."""
        try:
            from app.standalone.config import get_appdata_dir

            config_path = str(get_appdata_dir() / 'config.json')

            message = f"""Configuration file location:

{config_path}

Edit config.json and restart the app to apply changes.

You can also access the data directory to view logs and database."""

            # Show message box using thread-safe helper
            show_message_box(
                "DeskPulse - Settings",
                message,
                0x0 | 0x40  # MB_OK | MB_ICONINFORMATION
            )

            logger.info("Settings menu shown")

        except Exception as e:
            logger.exception(f"Show settings error: {e}")
            self._show_toast(
                title="⚠️ Error",
                message=f"Failed to show settings: {e}",
                duration="short"
            )

    def _show_about(self):
        """Show about dialog with version and platform info."""
        try:
            import platform

            about_text = f"""DeskPulse - Standalone Edition
Version: 2.0.0

Platform: {platform.system()} {platform.release()} (Build {platform.version()})
Python: {platform.python_version()}

GitHub: github.com/EmekaOkaforTech/deskpulse
License: MIT

Real-time posture monitoring for better desk ergonomics."""

            # Show message box using thread-safe helper
            show_message_box(
                "About DeskPulse",
                about_text,
                0x0 | 0x40  # MB_OK | MB_ICONINFORMATION
            )

            logger.info("About dialog shown")

        except Exception as e:
            logger.exception(f"Show about error: {e}")
            self._show_toast(
                title="⚠️ Error",
                message=f"Failed to show about dialog: {e}",
                duration="short"
            )

    def _quit_app(self):
        """Quit application via menu."""
        logger.info("Quit requested via tray menu")

        # Show confirmation dialog using thread-safe helper
        result = show_message_box(
            "Quit DeskPulse",
            "Are you sure you want to quit DeskPulse?",
            0x4 | 0x20  # MB_YESNO | MB_ICONQUESTION
        )

        if result == 6:  # IDYES
            self.stop()

    def _log_metrics_if_due(self):
        """Log event processing metrics every 60 seconds."""
        current_time = time.time()

        if current_time - self._last_metrics_log >= 60:
            with self._metrics_lock:
                # Calculate latency statistics
                if self._latency_samples:
                    avg_latency = sum(self._latency_samples) / len(self._latency_samples)
                    sorted_samples = sorted(self._latency_samples)
                    p95_index = int(len(sorted_samples) * 0.95)
                    p95_latency = sorted_samples[p95_index] if p95_index < len(sorted_samples) else sorted_samples[-1]
                    min_latency = min(self._latency_samples)
                    max_latency = max(self._latency_samples)
                else:
                    avg_latency = p95_latency = min_latency = max_latency = 0

                # Get backend queue metrics
                queue_metrics = self.backend.get_queue_metrics()

                logger.info(
                    f"Event metrics: processed={self._events_processed}, "
                    f"latency(ms): avg={avg_latency:.1f}, p95={p95_latency:.1f}, "
                    f"min={min_latency:.1f}, max={max_latency:.1f}, "
                    f"queue: produced={queue_metrics['events_produced']}, "
                    f"dropped={queue_metrics['events_dropped']} ({queue_metrics['drop_rate_percent']}%)"
                )

                self._last_metrics_log = current_time

    def get_consumer_metrics(self) -> dict:
        """
        Get event consumer metrics.

        Returns:
            dict: Consumer metrics
                {
                    'events_processed': int,
                    'latency_avg_ms': float,
                    'latency_p95_ms': float,
                    'latency_samples': int
                }
        """
        with self._metrics_lock:
            if self._latency_samples:
                avg_latency = sum(self._latency_samples) / len(self._latency_samples)
                sorted_samples = sorted(self._latency_samples)
                p95_index = int(len(sorted_samples) * 0.95)
                p95_latency = sorted_samples[p95_index] if p95_index < len(sorted_samples) else sorted_samples[-1]
            else:
                avg_latency = p95_latency = 0

            return {
                'events_processed': self._events_processed,
                'latency_avg_ms': round(avg_latency, 2),
                'latency_p95_ms': round(p95_latency, 2),
                'latency_samples': len(self._latency_samples)
            }
