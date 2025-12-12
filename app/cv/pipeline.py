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

    def __init__(self, fps_target: int = 10):
        """
        Initialize CVPipeline with CV components.

        Args:
            fps_target: Target frames per second for processing (default 10)
                       Should match CAMERA_FPS_TARGET config for optimal
                       performance

        Raises:
            ValueError: If fps_target is zero or negative
        """
        from flask import current_app

        self.camera = None  # Initialized in start()
        self.detector = None
        self.classifier = None
        self.running = False
        self.thread = None

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
            self.camera = CameraCapture()
            self.detector = PoseDetector()
            self.classifier = PostureClassifier()

            # Initialize camera (Story 2.1 pattern)
            if not self.camera.initialize():
                logger.error(
                    "Failed to initialize camera - CV pipeline not started"
                )
                return False

            # Start processing thread
            self.running = True
            self.thread = threading.Thread(
                target=self._processing_loop,
                daemon=True,  # Thread terminates with main process
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

    def _processing_loop(self) -> None:
        """
        Main CV processing loop running in dedicated thread.

        Architecture:
        - Multi-threaded with queue-based messaging
        - OpenCV/MediaPipe release GIL during C/C++ processing (true
          parallelism)
        - FPS throttling prevents excessive CPU usage
        - Exception handling prevents thread crashes during 8+ hour operation

        Performance:
        - Target 10 FPS (100ms per frame budget)
        - MediaPipe: 150-200ms (exceeds budget, but acceptable for monitoring)
        - Actual FPS: 5-7 FPS on Pi 4, 8-10 FPS on Pi 5
        - Queue maxsize=1 ensures dashboard shows current state

        Error Handling:
        - Camera failures logged but don't crash thread (Story 2.7 will add
          reconnection)
        - MediaPipe errors logged and frame skipped
        - Thread continues running despite individual frame errors
        """
        frame_interval = 1.0 / self.fps_target  # 0.1 sec for 10 FPS
        last_frame_time = 0
        camera_failure_count = 0
        max_failure_log_rate = 10  # Log every 10th failure after threshold

        logger.info(
            f"CV processing loop started: fps_target={self.fps_target}, "
            f"frame_interval={frame_interval:.3f}s"
        )

        while self.running:
            current_time = time.time()

            # Throttle to target FPS
            if current_time - last_frame_time < frame_interval:
                time.sleep(0.01)  # Sleep 10ms to avoid busy-waiting
                continue

            last_frame_time = current_time

            try:
                # Step 1: Capture frame (Story 2.1)
                success, frame = self.camera.read_frame()
                if not success:
                    # Camera failure - log with rate limiting to prevent spam
                    # Story 2.7 will add reconnection logic
                    camera_failure_count += 1
                    if camera_failure_count % max_failure_log_rate == 1:
                        logger.warning(
                            f"Frame capture failed (count: "
                            f"{camera_failure_count}) - skipping frame"
                        )
                    time.sleep(0.1)  # Brief pause before retry
                    continue

                # Reset failure count on success
                if camera_failure_count > 0:
                    logger.info(
                        f"Camera recovered after {camera_failure_count} "
                        f"failures"
                    )
                    camera_failure_count = 0

                # Step 2: Detect pose landmarks (Story 2.2)
                # NOTE: detect_landmarks() releases GIL during MediaPipe
                # inference
                detection_result = self.detector.detect_landmarks(frame)

                # Step 3: Classify posture (Story 2.3)
                posture_state = self.classifier.classify_posture(
                    detection_result['landmarks']
                )

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
                    'frame_base64': frame_base64
                }

                # Step 7: Put result in queue (non-blocking, latest-wins)
                try:
                    cv_queue.put_nowait(cv_result)
                except queue.Full:
                    # Queue full - discard oldest result and add new one
                    cv_queue.get()  # Blocking OK - queue is full (maxsize=1)
                    cv_queue.put_nowait(cv_result)

                logger.debug(
                    f"CV frame processed: posture={posture_state}, "
                    f"user_present={detection_result['user_present']}, "
                    f"confidence={detection_result['confidence']:.2f}"
                )

            except (RuntimeError, ValueError, KeyError, OSError, TypeError,
                    AttributeError) as e:
                # Log exception but don't crash thread
                # Specific exceptions to avoid catching KeyboardInterrupt/SystemExit
                logger.exception(f"CV processing error: {e}")
                # Continue loop - next frame may succeed
                time.sleep(0.1)  # Brief pause to avoid error spam

        logger.info("CV processing loop terminated")
