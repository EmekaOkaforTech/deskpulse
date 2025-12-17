"""Multi-threaded CV pipeline for real-time posture monitoring.

This module provides the CVPipeline class that orchestrates camera capture,
pose detection, and posture classification in a dedicated thread.
"""

import threading
import queue
import time
import logging
import base64
from datetime import datetime

try:
    import cv2
except ImportError:
    cv2 = None  # For testing without OpenCV

from app.cv.capture import CameraCapture
from app.cv.detection import PoseDetector
from app.cv.classification import PostureClassifier
from app.extensions import socketio

logger = logging.getLogger('deskpulse.cv')

# Global queue for CV results (maxsize=1 keeps only latest state)
# Architecture decision: Latest-wins semantic for real-time data
cv_queue = queue.Queue(maxsize=1)


class CVPipeline:
    """
    Multi-threaded computer vision processing pipeline.

    Orchestrates camera capture, pose detection, and posture classification
    in a dedicated daemon thread, preventing CV processing from blocking
    Flask/SocketIO operations.

    Architecture:
    - Dedicated thread for CV processing (OpenCV/MediaPipe release GIL)
    - Queue-based communication (maxsize=1 for latest-wins semantic)
    - FPS throttling to prevent excessive CPU usage
    - JPEG compression for bandwidth optimization
    - Daemon thread for clean shutdown

    Performance:
    - Target 10 FPS (configurable via FPS_TARGET)
    - MediaPipe: 150-200ms per frame (bottleneck)
    - Queue overhead: <1ms (negligible)
    - JPEG encoding: 10-20ms (quality 80)

    Attributes:
        camera: CameraCapture instance for frame acquisition
        detector: PoseDetector instance for landmark detection
        classifier: PostureClassifier instance for posture classification
        running: Thread control flag (atomic bool)
        thread: Thread instance for CV processing loop
        fps_target: Target frames per second (from config, default 10)
    """

    def __init__(self, fps_target: int = 10, app=None):
        """
        Initialize CVPipeline with CV components.

        Args:
            fps_target: Target frames per second for processing (default 10)
                       Should match CAMERA_FPS_TARGET config for optimal
                       performance
            app: Flask application instance for background thread context
                (Story 3.6: Required for alert notifications in CV thread)

        Raises:
            ValueError: If fps_target is zero or negative
        """
        from flask import current_app

        self.app = app  # Store Flask app for background thread app context
        self.camera = None  # Initialized in start()
        self.detector = None
        self.classifier = None
        self.alert_manager = None  # Story 3.1 - Initialized in start()
        self.running = False
        self.thread = None

        # Camera state management (Story 2.7)
        self.camera_state = 'disconnected'  # connected/degraded/disconnected
        self.last_watchdog_ping = 0
        self.watchdog_interval = 15  # Send watchdog ping every 15 seconds

        # Load FPS target from config (defaults to 10 FPS)
        self.fps_target = current_app.config.get(
            'CAMERA_FPS_TARGET', fps_target
        )

        # Validate FPS target to prevent division by zero
        if self.fps_target <= 0:
            raise ValueError(
                f"fps_target must be positive, got {self.fps_target}"
            )

        logger.info(
            f"CVPipeline initialized: fps_target={self.fps_target}"
        )

    def start(self) -> bool:
        """
        Start CV processing in dedicated daemon thread.

        Returns:
            bool: True if pipeline started successfully, False otherwise

        Raises:
            No exceptions raised - errors logged and False returned
        """
        if self.running:
            logger.warning("CV pipeline already running")
            return False

        try:
            # Initialize CV components (requires Flask app context)
            # Import AlertManager here to ensure Flask app context is available
            # CRITICAL: AlertManager.__init__ calls current_app.config.get()
            # current_app only available inside Flask app context (after create_app())
            # Module-level import would fail: "Working outside of application context"
            from app.alerts.manager import AlertManager
            from app.alerts.notifier import send_alert_notification, send_confirmation  # Story 3.2, 3.5

            self.camera = CameraCapture()
            self.detector = PoseDetector()
            self.classifier = PostureClassifier()
            self.alert_manager = AlertManager()  # Story 3.1

            # Store as instance attribute for _processing_loop access
            self.send_alert_notification = send_alert_notification  # Story 3.2
            self.send_confirmation = send_confirmation  # Story 3.5

            # Initialize camera (Story 2.1 pattern)
            if not self.camera.initialize():
                logger.error(
                    "Failed to initialize camera"
                )
                self._emit_camera_status('disconnected')
                # Don't fail startup - camera may connect later
                # Thread will retry connection

            # Start processing thread
            # NOTE: daemon=False to allow proper camera access (OpenCV limitation)
            # Cleanup registered via atexit in app/__init__.py
            self.running = True
            self.thread = threading.Thread(
                target=self._processing_loop,
                daemon=False,  # Non-daemon for camera access compatibility
                name=f'CVPipeline-{id(self)}'
            )
            self.thread.start()

            logger.info("CV pipeline started in dedicated thread")
            return True

        except Exception as e:
            logger.exception(f"Failed to start CV pipeline: {e}")
            self.running = False
            return False

    def stop(self) -> None:
        """
        Stop CV processing gracefully.

        Waits up to 5 seconds for thread to terminate, then releases camera.
        Safe to call multiple times.
        """
        if not self.running:
            logger.debug("CV pipeline already stopped")
            return

        logger.info("Stopping CV pipeline...")
        self.running = False

        # Wait for thread to terminate (max 5 seconds)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                logger.warning(
                    "CV pipeline thread did not terminate within timeout"
                )

        # Release camera resources
        if self.camera:
            self.camera.release()
            logger.info("Camera released")

        logger.info("CV pipeline stopped")

    def _send_watchdog_ping(self) -> None:
        """
        Send systemd watchdog ping (Layer 3 safety net).

        Pings sent every 15 seconds to systemd. If no ping received within
        30 seconds (WatchdogSec=30 in deskpulse.service), systemd restarts
        the service.

        Architecture: systemd Watchdog Safety Net (architecture.md:825-854)
        """
        current_time = time.time()

        if current_time - self.last_watchdog_ping > self.watchdog_interval:
            try:
                import sdnotify
                notifier = sdnotify.SystemdNotifier()
                notifier.notify("WATCHDOG=1")
                self.last_watchdog_ping = current_time
                logger.debug("systemd watchdog ping sent")

            except Exception as e:
                # Don't crash if sdnotify fails (may not be in systemd)
                logger.debug(f"Watchdog ping failed (not in systemd?): {e}")

    def _emit_camera_status(self, state: str) -> None:
        """
        Emit camera status to all connected SocketIO clients.

        Args:
            state: Camera state ('connected', 'degraded', 'disconnected')

        Raises:
            ValueError: If state is not a valid camera state
        """
        # Validate state value
        valid_states = ['connected', 'degraded', 'disconnected']
        if state not in valid_states:
            raise ValueError(
                f"Invalid camera state '{state}', "
                f"must be one of {valid_states}"
            )

        try:
            socketio.emit(
                'camera_status',
                {'state': state, 'timestamp': datetime.now().isoformat()}
            )
            logger.info(f"Camera status emitted: {state}")

        except Exception as e:
            # Don't crash if SocketIO emit fails
            logger.error(f"Failed to emit camera status: {e}")

    def _processing_loop(self) -> None:
        """
        CV processing loop with 3-layer camera recovery.

        Layer 1: Quick retries (3 attempts, ~2-3 seconds) for transient
                 USB glitches
        Layer 2: Long retry cycle (10 seconds) for sustained disconnects
                 (NFR-R4)
        Layer 3: systemd watchdog safety net (30 seconds) for Python crashes

        Architecture: Camera Failure Handling Strategy
                      (architecture.md:789-865)
        """
        logger.info("CV processing loop started")

        # Layer 1 recovery constants
        MAX_QUICK_RETRIES = 3
        QUICK_RETRY_DELAY = 1  # seconds

        # Layer 2 recovery constant
        LONG_RETRY_DELAY = 10  # seconds (NFR-R4 requirement)

        # Frame timing
        frame_delay = 1.0 / self.fps_target

        while self.running:
            try:
                # Send watchdog ping (Layer 3 safety net)
                # CRITICAL: Positioned at top of loop to ensure pings
                # continue during Layer 2 long retry (10 sec sleep).
                # Timing: 10s sleep + processing < 30s timeout.
                self._send_watchdog_ping()

                # Attempt frame capture
                ret, frame = self.camera.read_frame()

                if not ret:
                    # ============================================
                    # LAYER 1: Quick Retry Recovery (2-3 sec)
                    # ============================================
                    # Frame read failed - enter degradation
                    if self.camera_state == 'connected':
                        self.camera_state = 'degraded'
                        logger.warning("Camera degraded: frame read failed")
                        self._emit_camera_status('degraded')

                    # Quick retry loop for transient failures
                    reconnected = False
                    for attempt in range(1, MAX_QUICK_RETRIES + 1):
                        logger.info(
                            f"Camera quick retry {attempt}/"
                            f"{MAX_QUICK_RETRIES}"
                        )

                        # Release and reinitialize camera
                        self.camera.release()
                        time.sleep(QUICK_RETRY_DELAY)

                        if self.camera.initialize():
                            ret, frame = self.camera.read_frame()
                            if ret:
                                self.camera_state = 'connected'
                                logger.info(
                                    f"Camera reconnected after {attempt} "
                                    f"quick retries"
                                )
                                self._emit_camera_status('connected')
                                reconnected = True
                                break

                    if reconnected:
                        # Success - continue to normal processing
                        pass
                    else:
                        # ==========================================
                        # LAYER 2: Long Retry Cycle (10 sec - NFR-R4)
                        # ==========================================
                        # All quick retries failed - sustained disconnect
                        self.camera_state = 'disconnected'
                        logger.error(
                            "Camera disconnected: all quick retries failed"
                        )
                        self._emit_camera_status('disconnected')

                        # Wait 10 seconds before next retry cycle
                        # NFR-R4: 10-second camera reconnection requirement
                        logger.info(
                            f"Waiting {LONG_RETRY_DELAY}s before next "
                            f"reconnection attempt"
                        )
                        time.sleep(LONG_RETRY_DELAY)
                        continue  # Skip frame processing, retry capture

                else:
                    # ======================================
                    # Frame read successful - process it
                    # ======================================
                    # Restore state to connected if recovering
                    if self.camera_state != 'connected':
                        self.camera_state = 'connected'
                        logger.info("Camera restored to connected state")
                        self._emit_camera_status('connected')

                # Step 2: Detect pose landmarks (Story 2.2)
                # NOTE: detect_landmarks() releases GIL during MediaPipe
                # inference
                detection_result = self.detector.detect_landmarks(frame)

                # Step 3: Classify posture (Story 2.3)
                posture_state = self.classifier.classify_posture(
                    detection_result['landmarks']
                )

                # ==================================================
                # Story 3.1: Alert Threshold Tracking
                # ==================================================
                # Check for alerts (wrapped in try/except to prevent CV pipeline crashes)
                try:
                    alert_result = self.alert_manager.process_posture_update(
                        posture_state,
                        detection_result['user_present']
                    )
                except Exception as e:
                    # Alert processing should never crash CV pipeline
                    logger.exception(f"Alert processing error: {e}")
                    # Use safe default: no alert
                    alert_result = {
                        'should_alert': False,
                        'duration': 0,
                        'threshold_reached': False
                    }
                # ==================================================

                # ==================================================
                # Story 3.2: Alert Notification Delivery
                # ==================================================
                if alert_result['should_alert']:
                    logger.warning(f"🚨 ALERT TRIGGERED! Duration: {alert_result['duration']}s")
                    try:
                        # CRITICAL: Wrap in app context for background thread
                        # Flask's current_app is thread-local and unavailable in CV thread
                        # Without context, current_app.config.get() raises RuntimeError
                        # Story 3.6: Fix alert notifications in background thread
                        logger.info("Entering app context for notifications...")
                        with self.app.app_context():
                            logger.info("App context active, sending notifications...")

                            # Desktop notification (libnotify)
                            self.send_alert_notification(alert_result['duration'])
                            logger.info("Desktop notification sent")

                            # Browser notification (SocketIO - Story 3.3 preparation)
                            # NOTE: socketio import at module level is safe - already
                            # initialized in extensions.py before CV pipeline starts
                            from app.extensions import socketio
                            logger.info(f"Emitting alert_triggered event via SocketIO...")
                            socketio.emit('alert_triggered', {
                                'message': f"Bad posture detected for {alert_result['duration'] // 60} minutes",
                                'duration': alert_result['duration'],
                                'timestamp': datetime.now().isoformat()
                            })
                            logger.info("✅ alert_triggered event emitted successfully")

                    except Exception as e:
                        # Notification failures never crash CV pipeline
                        logger.exception(f"❌ Notification delivery failed: {e}")
                # ==================================================

                # ==================================================
                # Story 3.5: Posture Correction Confirmation
                # ==================================================
                if alert_result.get('posture_corrected'):
                    try:
                        # Story 3.6: Wrap in app context for background thread
                        with self.app.app_context():
                            # Desktop notification (send_confirmation imported at module level)
                            self.send_confirmation(alert_result['previous_duration'])

                            # Browser notification (SocketIO)
                            from app.extensions import socketio
                            socketio.emit('posture_corrected', {
                                'message': '✓ Good posture restored! Nice work!',
                                'previous_duration': alert_result['previous_duration'],
                                'timestamp': datetime.now().isoformat()
                            }, broadcast=True)

                            logger.info(
                                f"Posture correction confirmed: {alert_result['previous_duration']}s"
                            )

                    except Exception as e:
                        # Confirmation failures never crash CV pipeline
                        logger.exception(f"Correction notification failed: {e}")
                # ==================================================

                # Step 4: Draw skeleton overlay with color-coded posture
                overlay_color = self.classifier.get_landmark_color(
                    posture_state
                )
                annotated_frame = self.detector.draw_landmarks(
                    frame,
                    detection_result['landmarks'],
                    color=overlay_color
                )

                # Step 5: Encode frame for streaming (JPEG compression)
                if cv2 is not None:
                    # JPEG quality 80: Balance between bandwidth and visual
                    # quality
                    # Quality 80: ~20-30KB per frame (vs ~200KB uncompressed)
                    _, buffer = cv2.imencode(
                        '.jpg',
                        annotated_frame,
                        [cv2.IMWRITE_JPEG_QUALITY, 80]
                    )
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                else:
                    frame_base64 = None  # Testing without cv2

                # Step 6: Prepare result for queue
                cv_result = {
                    'timestamp': datetime.now().isoformat(),
                    'posture_state': posture_state,
                    'user_present': detection_result['user_present'],
                    'confidence_score': detection_result['confidence'],
                    'frame_base64': frame_base64,
                    'camera_state': self.camera_state,  # Story 2.7
                    'alert': alert_result  # Story 3.1 - consumed by Story 3.2, 3.3, 4.1
                }

                # Step 7: Put result in queue (non-blocking, latest-wins)
                try:
                    cv_queue.put_nowait(cv_result)
                except queue.Full:
                    # Queue full - discard oldest result and add new one
                    # Use get_nowait to prevent blocking, then put with timeout
                    try:
                        cv_queue.get_nowait()
                    except queue.Empty:
                        pass  # Queue emptied by consumer, continue
                    # Use put with timeout to handle race condition
                    try:
                        cv_queue.put(cv_result, timeout=0.1)
                    except queue.Full:
                        # Still full after get - log and drop frame
                        logger.warning("CV queue still full, dropping frame")

                logger.debug(
                    f"CV frame processed: posture={posture_state}, "
                    f"user_present={detection_result['user_present']}, "
                    f"confidence={detection_result['confidence']:.2f}"
                )

                # Frame rate throttling
                time.sleep(frame_delay)

            except OSError as e:
                # ======================================================
                # Camera hardware errors (USB disconnect, device failure)
                # ======================================================
                logger.exception(f"Camera hardware error: {e}")

                # Set camera state to degraded - this is a camera issue
                if self.camera_state == 'connected':
                    self.camera_state = 'degraded'
                    self._emit_camera_status('degraded')

                # Brief pause before retry
                time.sleep(1)

            except (RuntimeError, ValueError, KeyError, TypeError,
                    AttributeError) as e:
                # ======================================================
                # CV processing errors (MediaPipe, encoding, etc.)
                # These are NOT camera failures - don't change camera_state
                # ======================================================
                logger.exception(f"CV processing error: {e}")

                # Continue loop - Layer 3 (systemd watchdog) handles
                # true crashes if we stop sending watchdog pings
                time.sleep(1)  # Brief pause to avoid error spam

        logger.info("CV processing loop terminated")
