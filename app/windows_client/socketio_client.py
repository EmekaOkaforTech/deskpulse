"""DeskPulse Windows Desktop Client - SocketIO Client Wrapper."""
import logging
import socketio
import requests
import threading
import time
from typing import Optional, Dict, Any

logger = logging.getLogger('deskpulse.windows.socketio')


class SocketIOClient:
    """
    SocketIO client wrapper for Windows desktop client.

    Manages persistent WebSocket connection to Flask-SocketIO backend.
    Emits pause/resume events and listens for monitoring status updates.
    """

    def __init__(self, backend_url: str, tray_manager: Any, notifier: Any = None):
        """
        Initialize SocketIO client.

        Args:
            backend_url: Backend URL (e.g., http://raspberrypi.local:5000)
            tray_manager: Reference to TrayManager for icon updates
            notifier: Optional WindowsNotifier for toast notifications
        """
        self.backend_url = backend_url
        self.tray_manager = tray_manager
        self.notifier = notifier

        # Create SocketIO client with auto-reconnect
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_delay=5,
            reconnection_delay_max=30,
            logger=False,  # Disable socketio's verbose logging
            engineio_logger=False
        )

        # Register event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('monitoring_status', self.on_monitoring_status)
        self.sio.on('error', self.on_error)
        self.sio.on('alert_triggered', self.on_alert_triggered)
        self.sio.on('posture_corrected', self.on_posture_corrected)

        # Tooltip update thread (AC6: update every 60 seconds)
        self._tooltip_update_stop = threading.Event()
        self._tooltip_thread = None

        logger.info(f"SocketIO client initialized for {backend_url}")

    def on_connect(self):
        """
        Handle connection to backend.

        - Updates tray icon to green (monitoring state from backend)
        - Fetches /api/stats/today for tooltip
        - Emits request_status to get current monitoring state
        - Starts periodic tooltip update thread (AC6: 60s interval)
        - Shows connection notification (Story 7.2)
        """
        logger.info(f"Connected to backend: {self.backend_url}")

        # Update tray icon to connected state (will be updated by monitoring_status)
        if hasattr(self.tray_manager, 'update_icon_state'):
            self.tray_manager.update_icon_state('connected')

        # Show connected notification (Story 7.2)
        if self.notifier:
            self.notifier.show_connection_status(connected=True)

        # Fetch today's stats for tooltip (initial)
        self._update_tooltip_from_api()

        # Request current monitoring status
        # Backend will respond with monitoring_status event
        try:
            self.sio.emit('request_status')
            logger.info("Emitted request_status to backend")
        except Exception as e:
            logger.warning(f"Failed to emit request_status: {e}")

        # Start periodic tooltip update thread (AC6: every 60 seconds)
        self._start_tooltip_update_thread()

    def on_disconnect(self):
        """
        Handle disconnection from backend.

        - Updates tray icon to red (disconnected state)
        - Updates tooltip to show disconnected message
        - Stops periodic tooltip update thread
        - Shows disconnection notification (Story 7.2)

        CRITICAL FIX: Reset _emit_in_progress on disconnect to prevent permanent lock.
        """
        logger.info("Disconnected from backend")

        # Stop tooltip update thread
        self._stop_tooltip_update_thread()

        # Reset emit flag on disconnect to prevent lock (C2 fix)
        if hasattr(self.tray_manager, '_emit_in_progress'):
            self.tray_manager._emit_in_progress = False

        # Update tray icon to disconnected state
        if hasattr(self.tray_manager, 'update_icon_state'):
            self.tray_manager.update_icon_state('disconnected')

        # Show disconnected notification (Story 7.2)
        if self.notifier:
            self.notifier.show_connection_status(connected=False)

        # Update tooltip
        self.tray_manager.update_tooltip(None)

    def on_monitoring_status(self, data: Dict[str, Any]):
        """
        Handle monitoring status update from backend.

        Backend emits this event:
        - On connect (initial status)
        - When pause_monitoring is called
        - When resume_monitoring is called

        Args:
            data: Status data with 'monitoring_active' boolean
        """
        monitoring_active = data.get('monitoring_active', True)
        logger.info(f"Monitoring status update: monitoring_active={monitoring_active}")

        # Update tray manager state
        self.tray_manager.monitoring_active = monitoring_active

        # Clear any pending emit flag
        if hasattr(self.tray_manager, '_emit_in_progress'):
            self.tray_manager._emit_in_progress = False

        # Update icon: green if monitoring, gray if paused
        if hasattr(self.tray_manager, 'update_icon_state'):
            state = 'connected' if monitoring_active else 'paused'
            self.tray_manager.update_icon_state(state)

    def on_error(self, data: Dict[str, Any]):
        """
        Handle error event from backend.

        Backend emits this when pause/resume fails or other errors occur.

        Args:
            data: Error data with 'message' string
        """
        error_message = data.get('message', 'Unknown error')
        logger.error(f"Backend error: {error_message}")

        # Clear any pending emit flag
        if hasattr(self.tray_manager, '_emit_in_progress'):
            self.tray_manager._emit_in_progress = False

        # Show MessageBox to user
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"DeskPulse Backend Error\n\n{error_message}",
                "DeskPulse",
                0  # MB_OK
            )
        except Exception as e:
            logger.warning(f"Failed to show error MessageBox: {e}")

    def on_alert_triggered(self, data: Dict[str, Any]):
        """
        Handle posture alert event from backend (Story 7.2).

        Backend emits this when bad posture threshold exceeded.
        Event data from app/cv/pipeline.py:454.

        Args:
            data: Alert data with 'duration' (seconds), 'message', 'timestamp'
        """
        # Defensive extraction (handles missing field)
        duration_seconds = data.get('duration', 0)
        logger.info(f"alert_triggered event received: {duration_seconds}s")

        # Show notification if notifier available
        if self.notifier:
            self.notifier.show_posture_alert(duration_seconds)

    def on_posture_corrected(self, data: Dict[str, Any]):
        """
        Handle posture correction event from backend (Story 7.2).

        Backend emits this when user corrects posture after alert.
        Event data from app/cv/pipeline.py:478.

        Args:
            data: Correction data with 'message', 'previous_duration', 'timestamp'
        """
        logger.info("posture_corrected event received")

        # Optional: Extract previous_duration for future analytics
        previous_duration = data.get('previous_duration', 0)
        logger.debug(f"Posture corrected after {previous_duration}s in bad posture")

        # Show notification if notifier available
        if self.notifier:
            self.notifier.show_posture_corrected()

    def connect(self) -> bool:
        """
        Connect to backend.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.backend_url}")
            self.sio.connect(self.backend_url)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to backend: {e}")
            return False

    def disconnect(self):
        """Disconnect from backend."""
        try:
            # Stop tooltip update thread
            self._stop_tooltip_update_thread()

            if self.sio.connected:
                logger.info("Disconnecting from backend")
                self.sio.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def _update_tooltip_from_api(self):
        """
        Fetch stats from /api/stats/today and update tooltip.

        Runs in background thread to avoid blocking.
        """
        def fetch_and_update():
            try:
                response = requests.get(
                    f"{self.backend_url}/api/stats/today",
                    timeout=5
                )
                if response.status_code == 200:
                    stats = response.json()
                    self.tray_manager.update_tooltip(stats)
                    logger.debug("Tooltip updated from API")
                else:
                    logger.warning(f"Failed to fetch stats: {response.status_code}")
            except Exception as e:
                logger.warning(f"Error fetching stats: {e}")

        # Run in background thread (non-blocking)
        threading.Thread(target=fetch_and_update, daemon=True, name='StatsUpdate').start()

    def _tooltip_update_loop(self):
        """
        Periodic tooltip update loop (AC6: every 60 seconds).

        Runs in daemon thread, stops on disconnect or explicit stop.
        """
        logger.info("Tooltip update thread started (60s interval)")
        while not self._tooltip_update_stop.wait(60):
            if self.sio.connected:
                self._update_tooltip_from_api()
            else:
                break
        logger.info("Tooltip update thread stopped")

    def _start_tooltip_update_thread(self):
        """Start periodic tooltip update thread."""
        if self._tooltip_thread is None or not self._tooltip_thread.is_alive():
            self._tooltip_update_stop.clear()
            self._tooltip_thread = threading.Thread(
                target=self._tooltip_update_loop,
                daemon=True,
                name='TooltipUpdater'
            )
            self._tooltip_thread.start()

    def _stop_tooltip_update_thread(self):
        """Stop periodic tooltip update thread."""
        if self._tooltip_thread and self._tooltip_thread.is_alive():
            self._tooltip_update_stop.set()
            # Don't wait for thread to finish (daemon thread will exit on app close)

    def emit_pause(self):
        """
        Emit pause_monitoring event to backend.

        Backend will pause posture tracking and broadcast monitoring_status
        to all clients (including this one).

        CRITICAL FIX: Reset _emit_in_progress flag on error to prevent permanent lock.
        """
        try:
            logger.info("Emitting pause_monitoring to backend")
            self.sio.emit('pause_monitoring')
        except Exception as e:
            logger.error(f"Error emitting pause_monitoring: {e}")
            # Reset flag on error to prevent permanent lock (C2 fix)
            if hasattr(self.tray_manager, '_emit_in_progress'):
                self.tray_manager._emit_in_progress = False

    def emit_resume(self):
        """
        Emit resume_monitoring event to backend.

        Backend will resume posture tracking and broadcast monitoring_status
        to all clients (including this one).

        CRITICAL FIX: Reset _emit_in_progress flag on error to prevent permanent lock.
        """
        try:
            logger.info("Emitting resume_monitoring to backend")
            self.sio.emit('resume_monitoring')
        except Exception as e:
            logger.error(f"Error emitting resume_monitoring: {e}")
            # Reset flag on error to prevent permanent lock (C2 fix)
            if hasattr(self.tray_manager, '_emit_in_progress'):
                self.tray_manager._emit_in_progress = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to backend."""
        return self.sio.connected
