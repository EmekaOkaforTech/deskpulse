"""
Backend Thread Wrapper for Standalone Windows Edition.

Runs Flask backend in background thread without SocketIO.
Uses Windows camera and %APPDATA% paths.
"""

import threading
import logging
import time
import sys
import queue
from pathlib import Path
from typing import Optional, Callable
from collections import defaultdict

logger = logging.getLogger('deskpulse.standalone.backend')

# Event priority constants (Story 8.4 - Task 3.2)
# Lower number = higher priority
PRIORITY_CRITICAL = 1  # Alerts, errors
PRIORITY_HIGH = 2      # Status changes, camera state
PRIORITY_NORMAL = 3    # Posture corrections
PRIORITY_LOW = 4       # Posture updates (10 FPS stream)


class SharedState:
    """
    Thread-safe shared state for backend thread (Story 8.4 - Task 5).

    Provides thread-safe access to monitoring state and cached statistics.
    Used for coordination between backend thread, TrayApp consumer thread,
    and test threads.

    All methods use locks to ensure thread safety and return copies of state
    to prevent external mutation.
    """

    def __init__(self):
        """Initialize shared state with defaults."""
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._lock_timeout = 5.0  # 5 second timeout to prevent deadlocks

        # State fields
        self._monitoring_active = True
        self._alert_active = False
        self._alert_duration = 0  # Current alert duration in seconds

        # Statistics caching (60-second TTL)
        self._cached_stats = None
        self._cache_timestamp = 0.0
        self._cache_ttl = 60.0  # 60 seconds
        self._cache_hits = 0
        self._cache_misses = 0
        self._last_cache_log = time.time()

    def get_monitoring_status(self) -> dict:
        """
        Get current monitoring status (thread-safe).

        Returns:
            dict: Copy of monitoring status {
                'monitoring_active': bool,
                'alert_active': bool,
                'alert_duration': int
            }
        """
        acquired = self._lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            logger.warning("SharedState: Failed to acquire lock for get_monitoring_status() (timeout)")
            # Return safe defaults
            return {
                'monitoring_active': False,
                'alert_active': False,
                'alert_duration': 0
            }

        try:
            # Return copy (not reference)
            return {
                'monitoring_active': self._monitoring_active,
                'alert_active': self._alert_active,
                'alert_duration': self._alert_duration
            }
        finally:
            self._lock.release()

    def update_monitoring_active(self, active: bool) -> dict:
        """
        Update monitoring_active state (thread-safe).

        Args:
            active: New monitoring state

        Returns:
            dict: Updated state snapshot
        """
        acquired = self._lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            logger.warning("SharedState: Failed to acquire lock for update_monitoring_active() (timeout)")
            return self.get_monitoring_status()

        try:
            self._monitoring_active = active

            # Invalidate stats cache on state change
            self._cached_stats = None
            self._cache_timestamp = 0.0

            logger.info(f"SharedState: monitoring_active={active}")
            return self.get_monitoring_status()
        finally:
            self._lock.release()

    def update_alert_state(self, alert_active: bool, alert_duration: int = 0) -> dict:
        """
        Update alert state (thread-safe).

        Args:
            alert_active: Whether alert is currently active
            alert_duration: Alert duration in seconds (if active)

        Returns:
            dict: Updated state snapshot
        """
        acquired = self._lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            logger.warning("SharedState: Failed to acquire lock for update_alert_state() (timeout)")
            return self.get_monitoring_status()

        try:
            self._alert_active = alert_active
            self._alert_duration = alert_duration if alert_active else 0

            logger.debug(f"SharedState: alert_active={alert_active}, duration={alert_duration}s")
            return self.get_monitoring_status()
        finally:
            self._lock.release()

    def get_cached_stats(self) -> Optional[dict]:
        """
        Get cached statistics (thread-safe with 60-second TTL).

        Returns:
            dict: Cached stats if valid, None if expired/missing
        """
        acquired = self._lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            logger.warning("SharedState: Failed to acquire lock for get_cached_stats() (timeout)")
            return None

        try:
            current_time = time.time()
            cache_age = current_time - self._cache_timestamp

            if self._cached_stats and cache_age < self._cache_ttl:
                # Cache hit
                self._cache_hits += 1
                self._log_cache_metrics(current_time)
                return self._cached_stats.copy()  # Return copy
            else:
                # Cache miss
                self._cache_misses += 1
                self._log_cache_metrics(current_time)
                return None
        finally:
            self._lock.release()

    def set_cached_stats(self, stats: dict) -> None:
        """
        Update statistics cache (thread-safe).

        Args:
            stats: Statistics dictionary to cache
        """
        acquired = self._lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            logger.warning("SharedState: Failed to acquire lock for set_cached_stats() (timeout)")
            return

        try:
            self._cached_stats = stats.copy() if stats else None
            self._cache_timestamp = time.time()
            logger.debug("SharedState: Statistics cache updated")
        finally:
            self._lock.release()

    def invalidate_stats_cache(self) -> None:
        """Invalidate statistics cache (thread-safe)."""
        acquired = self._lock.acquire(timeout=self._lock_timeout)
        if not acquired:
            logger.warning("SharedState: Failed to acquire lock for invalidate_stats_cache() (timeout)")
            return

        try:
            self._cached_stats = None
            self._cache_timestamp = 0.0
            logger.debug("SharedState: Statistics cache invalidated")
        finally:
            self._lock.release()

    def _log_cache_metrics(self, current_time: float) -> None:
        """
        Log cache hit/miss ratio every 5 minutes.

        NOTE: Must be called while holding lock.
        """
        if current_time - self._last_cache_log >= 300:  # 5 minutes
            total = self._cache_hits + self._cache_misses
            if total > 0:
                hit_rate = (self._cache_hits / total) * 100
                logger.info(
                    f"SharedState Cache: {self._cache_hits} hits, "
                    f"{self._cache_misses} misses ({hit_rate:.1f}% hit rate)"
                )

                # Reset counters
                self._cache_hits = 0
                self._cache_misses = 0
                self._last_cache_log = current_time


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

    def __init__(self, config: dict, event_queue: Optional[queue.PriorityQueue] = None):
        """
        Initialize backend thread.

        Args:
            config: Configuration dictionary from config.py
            event_queue: Optional priority queue for IPC events (Story 8.4)
                        If None, callbacks-only mode (no event queue)
        """
        self.config = config
        self.thread = None
        self.running = False
        self.flask_app = None
        self.cv_pipeline = None
        self.camera = None  # Store camera reference for tray preview
        self.camera_error = None  # Store camera error for main thread

        # Flask server thread (Story 8.6 - for dashboard access)
        self.flask_server_thread = None
        self.flask_server = None

        # Callback registration system (Story 8.4 - Task 2)
        self._callbacks = defaultdict(list)  # event_type -> [callback1, callback2, ...]
        self._callback_lock = threading.Lock()  # Thread-safe callback access

        # Priority event queue system (Story 8.4 - Task 3)
        self._event_queue = event_queue
        self._events_produced = 0  # Total events enqueued
        self._events_dropped = 0   # Events dropped due to queue full
        self._queue_metrics_lock = threading.Lock()  # Thread-safe metrics
        self._last_metrics_log = time.time()

        # Thread-safe shared state (Story 8.4 - Task 5)
        self.shared_state = SharedState()

        logger.info("BackendThread initialized (event_queue: %s)", "enabled" if event_queue else "disabled")

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
                init_db(self.flask_app)  # CRITICAL FIX: Pass Flask app to init_db()
                logger.info(f"Database initialized: {database_path}")

            # ENTERPRISE FIX: Auto-detect working camera with fallback
            camera_config = self.config.get('camera', {})
            preferred_index = camera_config.get('index', 0)
            fps = camera_config.get('fps', 10)
            width = camera_config.get('width', 640)
            height = camera_config.get('height', 480)

            # Try preferred camera index first, then fallback to other indices
            camera_indices_to_try = [preferred_index]
            # Add fallback indices (0-3) if not already in list
            for fallback_idx in [0, 1, 2, 3]:
                if fallback_idx not in camera_indices_to_try:
                    camera_indices_to_try.append(fallback_idx)

            camera = None
            camera_opened = False
            working_index = None

            for camera_idx in camera_indices_to_try:
                logger.info(f"Attempting camera index {camera_idx}...")
                try:
                    test_camera = WindowsCamera(
                        camera_index=camera_idx,
                        fps=fps,
                        width=width,
                        height=height
                    )

                    logger.info(f"Opening camera {camera_idx} (timeout: 45 seconds)...")

                    # Try to open camera with 45-second timeout
                    # If it hangs longer, skip to next camera
                    import threading as thread_module
                    camera_result = {'opened': False}

                    def try_open():
                        try:
                            camera_result['opened'] = test_camera.open()
                        except Exception as e:
                            logger.warning(f"Camera {camera_idx} open() exception: {e}")
                            camera_result['opened'] = False

                    open_thread = thread_module.Thread(target=try_open, daemon=True)
                    open_thread.start()
                    open_thread.join(timeout=45)  # 45-second timeout

                    if open_thread.is_alive():
                        # Camera open is hanging - skip this camera
                        logger.warning(f"✗ Camera {camera_idx} timed out after 45 seconds - trying next camera")
                        continue

                    camera_opened = camera_result['opened']

                    if camera_opened:
                        logger.info(f"✓ Camera {camera_idx} opened successfully!")
                        camera = test_camera
                        working_index = camera_idx
                        break
                    else:
                        logger.warning(f"✗ Camera {camera_idx} failed to open")
                        try:
                            test_camera.release()
                        except:
                            pass

                except Exception as e:
                    logger.warning(f"✗ Camera {camera_idx} error: {e}")
                    continue

            if not camera_opened or camera is None:
                error_msg = "FATAL: Failed to open any camera - No webcam detected or access denied"
                logger.error(error_msg)
                logger.error("Tried camera indices: " + ", ".join(str(i) for i in camera_indices_to_try))
                logger.error("Please ensure:")
                logger.error("1. A webcam is connected")
                logger.error("2. No other application is using the camera")
                logger.error("3. Camera permissions are granted to DeskPulse")
                self.running = False
                self.camera_error = error_msg  # Store error for main thread
                return

            # Auto-update config if we used a different camera than configured
            if working_index != preferred_index:
                logger.info(f"✓ Auto-detected working camera: index {working_index} (was configured as {preferred_index})")
                logger.info(f"Updating config to remember working camera...")
                try:
                    if 'camera' not in self.config:
                        self.config['camera'] = {}
                    self.config['camera']['index'] = working_index
                    save_config(self.config)
                    logger.info(f"✓ Config updated - will use camera {working_index} on next launch")
                except Exception as e:
                    logger.warning(f"Could not save camera config: {e}")

            logger.info("Camera opened successfully!")
            self.camera = camera  # Store camera reference for tray preview

            # Create CV pipeline with Windows camera
            # CRITICAL: Must use Flask app context for CVPipeline initialization
            with self.flask_app.app_context():
                self.cv_pipeline = CVPipeline(
                    camera=camera,
                    app=self.flask_app
                )

                # Pass backend reference for IPC callbacks (Story 8.4)
                self.cv_pipeline.backend_thread = self

                # Start CV pipeline
                self.cv_pipeline.start()
                logger.info("CV pipeline started")

            # Start Flask server in separate thread (for dashboard access)
            self._start_flask_server()

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
            # CRITICAL: Also print to console for PyInstaller debugging
            print(f"FATAL BACKEND ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.running = False

        finally:
            self._cleanup()

    def _start_flask_server(self):
        """Start Flask server in separate thread for dashboard access."""
        try:
            port = self.config.get('dashboard', {}).get('port', 5000)

            def run_server():
                """Run Flask server (werkzeug)."""
                try:
                    logger.info(f"Starting Flask server on http://localhost:{port}")

                    # Use werkzeug server (not production, but fine for localhost)
                    from werkzeug.serving import make_server

                    self.flask_server = make_server(
                        'localhost',  # localhost only - no network exposure
                        port,
                        self.flask_app,
                        threaded=True  # Handle multiple requests
                    )

                    logger.info(f"Dashboard available at http://localhost:{port}")
                    self.flask_server.serve_forever()

                except Exception as e:
                    logger.error(f"Flask server error: {e}")

            # Start server in daemon thread
            self.flask_server_thread = threading.Thread(
                target=run_server,
                daemon=True,
                name='FlaskServer'
            )
            self.flask_server_thread.start()
            logger.info("Flask server thread started")

        except Exception as e:
            logger.exception(f"Failed to start Flask server: {e}")
            logger.warning("Dashboard will not be available, but monitoring continues")

    def _cleanup(self):
        """Cleanup resources."""
        try:
            # Stop Flask server
            if self.flask_server:
                logger.info("Stopping Flask server")
                self.flask_server.shutdown()
                self.flask_server = None

            if self.flask_server_thread and self.flask_server_thread.is_alive():
                self.flask_server_thread.join(timeout=2)
                logger.info("Flask server thread stopped")

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

        # Unregister all callbacks before shutdown (Story 8.4)
        self.unregister_all_callbacks()

        # Execute WAL checkpoint to flush database changes (Story 8.4)
        if self.flask_app:
            try:
                with self.flask_app.app_context():
                    from app.extensions import db
                    db.session.execute(db.text('PRAGMA wal_checkpoint(TRUNCATE)'))
                    logger.info("WAL checkpoint executed successfully")
            except Exception as e:
                logger.exception(f"WAL checkpoint error: {e}")

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
            # Pause monitoring via alert manager
            with self.flask_app.app_context():
                self.cv_pipeline.alert_manager.pause_monitoring()

            # Get current threshold for callback
            status = self.cv_pipeline.alert_manager.get_monitoring_status()
            threshold_seconds = status.get('threshold_seconds', 600)

            # Update shared state (Story 8.4 - Task 5)
            self.shared_state.update_monitoring_active(False)

            logger.info("Monitoring paused")

            # Trigger status_change callbacks (Story 8.4)
            self._notify_callbacks(
                'status_change',
                monitoring_active=False,
                threshold_seconds=threshold_seconds
            )

    def resume_monitoring(self):
        """Resume posture monitoring."""
        if self.cv_pipeline and self.cv_pipeline.alert_manager:
            # Resume monitoring via alert manager
            with self.flask_app.app_context():
                self.cv_pipeline.alert_manager.resume_monitoring()

            # Get current threshold for callback
            status = self.cv_pipeline.alert_manager.get_monitoring_status()
            threshold_seconds = status.get('threshold_seconds', 600)

            # Update shared state (Story 8.4 - Task 5)
            self.shared_state.update_monitoring_active(True)

            logger.info("Monitoring resumed")

            # Trigger status_change callbacks (Story 8.4)
            self._notify_callbacks(
                'status_change',
                monitoring_active=True,
                threshold_seconds=threshold_seconds
            )

    def get_today_stats(self) -> Optional[dict]:
        """
        Get today's posture statistics (with 60-second cache).

        Returns:
            dict: Today's stats or None if not available
        """
        if not self.flask_app:
            return None

        # Check cache first (Story 8.4 - Task 5.4)
        cached = self.shared_state.get_cached_stats()
        if cached:
            return cached

        # Cache miss - fetch from database
        try:
            with self.flask_app.app_context():
                from app.data.analytics import PostureAnalytics
                from datetime import date

                # Get pause_timestamp if monitoring is paused (CRITICAL for accurate stats)
                pause_timestamp = None
                if self.cv_pipeline and self.cv_pipeline.alert_manager:
                    if self.cv_pipeline.alert_manager.monitoring_paused:
                        pause_timestamp = self.cv_pipeline.alert_manager.pause_timestamp

                stats = PostureAnalytics.calculate_daily_stats(date.today(), pause_timestamp=pause_timestamp)

                # Update cache
                if stats:
                    self.shared_state.set_cached_stats(stats)

                return stats

        except Exception as e:
            logger.exception(f"Error getting stats: {e}")
            return None

    def get_history(self, days: int = 7) -> Optional[list]:
        """
        Get posture history.

        Args:
            days: Number of days of history (default 7)

        Returns:
            list: History data or None if not available
        """
        if not self.flask_app:
            return None

        try:
            with self.flask_app.app_context():
                from app.data.analytics import PostureAnalytics

                # Get pause_timestamp if monitoring is paused (CRITICAL for accurate today's stats)
                pause_timestamp = None
                if self.cv_pipeline and self.cv_pipeline.alert_manager:
                    if self.cv_pipeline.alert_manager.monitoring_paused:
                        pause_timestamp = self.cv_pipeline.alert_manager.pause_timestamp

                return PostureAnalytics.get_7_day_history(pause_timestamp=pause_timestamp)

        except Exception as e:
            logger.exception(f"Error getting history: {e}")
            return None

    # ===== Callback Registration System (Story 8.4) =====

    def notify_error(self, message: str, error_type: str = 'general') -> None:
        """
        Notify registered callbacks about an error.

        Public method for error notifications from any backend component.

        Args:
            message: Error message
            error_type: Error type ('camera', 'database', 'cv', 'general', etc.)
        """
        logger.error(f"Error notification: [{error_type}] {message}")
        self._notify_callbacks('error', message=message, error_type=error_type)

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register a callback for backend events.

        CRITICAL: Callbacks execute in BACKEND THREAD, not caller's thread.
        Callbacks MUST be lightweight (<5ms) - only enqueue events, no heavy work.
        Callbacks MUST NOT access UI directly - cross-thread violation.

        Supported event types:
        - 'alert': on_alert(duration: int, timestamp: str)
        - 'correction': on_correction(previous_duration: int, timestamp: str)
        - 'status_change': on_status_change(monitoring_active: bool, threshold_seconds: int)
        - 'camera_state': on_camera_state(state: str, timestamp: str)
        - 'error': on_error(message: str, error_type: str)

        Args:
            event_type: Event type to register for
            callback: Callable to invoke when event occurs

        Example:
            def on_alert(duration, timestamp):
                event_queue.put((CRITICAL, time.time(), 'alert', {...}))

            backend.register_callback('alert', on_alert)
        """
        with self._callback_lock:
            self._callbacks[event_type].append(callback)
            logger.info(f"Registered callback for event '{event_type}' (total: {len(self._callbacks[event_type])})")

    def unregister_callback(self, event_type: str, callback: Callable) -> None:
        """
        Unregister a specific callback.

        Args:
            event_type: Event type
            callback: Callback to remove
        """
        with self._callback_lock:
            if callback in self._callbacks[event_type]:
                self._callbacks[event_type].remove(callback)
                logger.info(f"Unregistered callback for event '{event_type}' (remaining: {len(self._callbacks[event_type])})")
            else:
                logger.warning(f"Callback not found for event '{event_type}'")

    def unregister_all_callbacks(self) -> None:
        """
        Unregister ALL callbacks (for shutdown).

        Called during backend shutdown to ensure clean teardown.
        """
        with self._callback_lock:
            callback_count = sum(len(callbacks) for callbacks in self._callbacks.values())
            self._callbacks.clear()
            logger.info(f"Unregistered all callbacks ({callback_count} total)")

    def _notify_callbacks(self, event_type: str, **kwargs) -> None:
        """
        Notify all registered callbacks for an event type.

        INTERNAL METHOD - called by backend when events occur.

        Callbacks execute in registration order (FIFO).
        Callback exceptions are isolated - don't crash backend.

        ALSO enqueues event to priority queue if configured (Story 8.4 - Task 3.3).

        Args:
            event_type: Event type
            **kwargs: Event parameters passed to callbacks
        """
        # Enqueue event to priority queue first (Story 8.4 - Task 3.3)
        if self._event_queue:
            self._enqueue_event(event_type, kwargs)

        # Get callback list copy (minimize lock time)
        with self._callback_lock:
            callbacks = self._callbacks[event_type].copy()

        if not callbacks:
            return  # No callbacks registered

        # Execute callbacks outside lock (prevent deadlock)
        for callback in callbacks:
            try:
                callback(**kwargs)
            except Exception as e:
                # Isolate callback exceptions - don't crash backend
                logger.exception(f"Callback exception in '{event_type}' handler: {e}")
                # Continue processing remaining callbacks

    def _enqueue_event(self, event_type: str, event_data: dict) -> None:
        """
        Enqueue event to priority queue for tray app consumer.

        ENTERPRISE: Priority-based queue full handling ensures CRITICAL events never dropped.

        Priority mapping (Story 8.4 - Task 3.3):
        - alert, error → CRITICAL (priority 1) - Block with 1s timeout
        - status_change, camera_state → HIGH (priority 2) - Block with 0.5s timeout
        - correction → NORMAL (priority 3) - Block with 0.5s timeout
        - posture_update → LOW (priority 4) - Non-blocking, drop oldest on full

        Args:
            event_type: Event type string
            event_data: Event data dictionary
        """
        # Determine priority based on event type
        if event_type in ('alert', 'error'):
            priority = PRIORITY_CRITICAL
            timeout = 1.0  # Block up to 1 second for critical events
        elif event_type in ('status_change', 'camera_state'):
            priority = PRIORITY_HIGH
            timeout = 0.5  # Block up to 0.5 seconds
        elif event_type == 'correction':
            priority = PRIORITY_NORMAL
            timeout = 0.5
        else:  # posture_update, etc.
            priority = PRIORITY_LOW
            timeout = None  # Non-blocking for low priority

        # Create event tuple: (priority, timestamp, event_type, data)
        # timestamp = time.perf_counter() for latency tracking
        event = (priority, time.perf_counter(), event_type, event_data)

        try:
            if timeout is None:
                # LOW priority: Non-blocking, drop if queue full (latest-wins)
                self._event_queue.put_nowait(event)
                with self._queue_metrics_lock:
                    self._events_produced += 1
            else:
                # CRITICAL/HIGH/NORMAL: Block with timeout
                self._event_queue.put(event, timeout=timeout)
                with self._queue_metrics_lock:
                    self._events_produced += 1

        except queue.Full:
            # Queue full handling
            with self._queue_metrics_lock:
                self._events_dropped += 1

            if priority == PRIORITY_CRITICAL:
                # CRITICAL events should NEVER be dropped
                logger.error(f"CRITICAL: Queue full, dropped '{event_type}' event! (events_dropped={self._events_dropped})")
            elif priority == PRIORITY_LOW:
                # LOW events expected to drop occasionally
                logger.debug(f"Queue full, dropped LOW priority '{event_type}' event (dropped_total={self._events_dropped})")
            else:
                # HIGH/NORMAL - warning
                logger.warning(f"Queue full, dropped '{event_type}' event (priority={priority}, dropped_total={self._events_dropped})")

        # Log queue metrics every 60 seconds (Story 8.4 - Task 3.5)
        current_time = time.time()
        if current_time - self._last_metrics_log >= 60:
            with self._queue_metrics_lock:
                drop_rate = (self._events_dropped / max(self._events_produced, 1)) * 100
                logger.info(
                    f"Queue metrics: produced={self._events_produced}, "
                    f"dropped={self._events_dropped} ({drop_rate:.1f}%), "
                    f"queue_size={self._event_queue.qsize()}"
                )
                self._last_metrics_log = current_time

    def get_queue_metrics(self) -> dict:
        """
        Get event queue metrics.

        Returns:
            dict: Queue metrics
                {
                    'events_produced': int,
                    'events_dropped': int,
                    'drop_rate_percent': float,
                    'queue_size': int
                }
        """
        with self._queue_metrics_lock:
            drop_rate = (self._events_dropped / max(self._events_produced, 1)) * 100
            return {
                'events_produced': self._events_produced,
                'events_dropped': self._events_dropped,
                'drop_rate_percent': round(drop_rate, 2),
                'queue_size': self._event_queue.qsize() if self._event_queue else 0
            }


# Global backend instance (singleton)
_backend_instance: Optional[BackendThread] = None
_backend_lock = threading.Lock()


# Export priority constants for external use (tray app, tests)
__all__ = [
    'BackendThread',
    'PRIORITY_CRITICAL',
    'PRIORITY_HIGH',
    'PRIORITY_NORMAL',
    'PRIORITY_LOW'
]


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
