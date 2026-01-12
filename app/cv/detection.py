"""
Story 2.2: Pose Detection with MediaPipe
Story 8.2: MediaPipe Tasks API Migration

This module provides pose detection capabilities using Google's MediaPipe library.
It detects 33 body landmarks for posture analysis.

**Technical Approach:**
- Uses MediaPipe Tasks API (PoseLandmarker) - migrated from deprecated Solutions API
- Processes BGR frames from OpenCV
- Returns normalized landmarks and confidence scores
- Thread-safe for background execution

**FR2: Real-Time Pose Landmark Detection**
- Detects 33 landmarks including shoulders, hips, spine
- Confidence scoring (0.0-1.0) based on nose landmark visibility
- Graceful degradation when user not in frame

**FR4: Visual Feedback**
- draw_landmarks() renders skeleton overlay on video feed
- Color-coded visualization (green for good posture, red for bad)

**Migration Notes (Story 8.2):**
- Migrated from mp.solutions.pose (deprecated) to mp.tasks.vision.PoseLandmarker
- Model files stored in app/cv/models/ directory
- Landmark access changed from protobuf to list structure
- Added timestamp tracking for VIDEO running mode
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger('deskpulse.cv.detection')

# Optional MediaPipe import with fallback
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    logger.info("MediaPipe imported successfully")
except ImportError as e:
    mp = None
    logger.error(f"MediaPipe import failed: {e}")
    logger.error("Pose detection will not be available.")
except Exception as e:
    mp = None
    logger.error(f"MediaPipe import error (unexpected): {e}")
    logger.error("Pose detection will not be available.")


class PoseDetector:
    """
    Detects human pose landmarks using MediaPipe Tasks API (Story 8.2).

    This class provides real-time pose detection for posture monitoring.
    It's designed to run in a background thread as part of the CV pipeline.

    **Configuration:**
    - Loads settings from Flask app config (Story 1.3)
    - Uses model files from app/cv/models/ directory
    - Configurable confidence thresholds

    **Thread Safety:**
    - MediaPipe PoseLandmarker is thread-safe via GIL
    - Each PoseDetector instance maintains its own landmarker context
    - Safe to use in CVPipeline background thread

    **Enterprise Considerations:**
    - Graceful error handling (returns None on failure)
    - Logging for debugging and monitoring
    - Resource cleanup in close()
    """

    def __init__(self, app=None):
        """
        Initialize PoseDetector with MediaPipe Tasks API (Story 8.2).

        Args:
            app: Flask application instance (for config access via Story 1.3)
        """
        if mp is None:
            raise ImportError("MediaPipe is not installed. Install with: pip install mediapipe")

        # Load configuration from app config (Story 1.3 pattern)
        if app:
            model_file = app.config.get('MEDIAPIPE_MODEL_FILE', 'pose_landmarker_full.task')
            min_detection_conf = app.config.get('MEDIAPIPE_MIN_DETECTION_CONFIDENCE', 0.5)
            min_tracking_conf = app.config.get('MEDIAPIPE_MIN_TRACKING_CONFIDENCE', 0.5)
        else:
            # Fallback to Flask current_app if app not provided
            from flask import current_app
            model_file = current_app.config.get('MEDIAPIPE_MODEL_FILE', 'pose_landmarker_full.task')
            min_detection_conf = current_app.config.get('MEDIAPIPE_MIN_DETECTION_CONFIDENCE', 0.5)
            min_tracking_conf = current_app.config.get('MEDIAPIPE_MIN_TRACKING_CONFIDENCE', 0.5)

        # Resolve model path (relative to this file)
        model_path = self._resolve_model_path(model_file)

        # Create PoseLandmarkerOptions (Tasks API)
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,  # Video stream mode (not static images)
            num_poses=1,  # Detect single person (optimal for DeskPulse use case)
            min_pose_detection_confidence=min_detection_conf,
            min_pose_presence_confidence=min_detection_conf,  # Same as detection threshold
            min_tracking_confidence=min_tracking_conf,
            output_segmentation_masks=False  # Disable to save CPU (like enable_segmentation=False)
        )

        # Create PoseLandmarker instance (Tasks API)
        try:
            self.landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe PoseLandmarker: {e}")
            raise RuntimeError(f"MediaPipe PoseLandmarker initialization failed: {e}") from e

        # Frame counter for timestamp generation (VIDEO mode requires timestamps)
        self.frame_counter = 0

        # Store drawing utilities (optional - only needed for visualization)
        # Try to import from Solutions API, but make it optional for Tasks API compatibility
        try:
            self.mp_drawing = mp.solutions.drawing_utils
            self.mp_pose = mp.solutions.pose  # Keep for POSE_CONNECTIONS constant
            logger.info("MediaPipe drawing utilities loaded successfully")
        except (AttributeError, ImportError) as e:
            self.mp_drawing = None
            self.mp_pose = None
            logger.warning(f"MediaPipe drawing utilities not available: {e}")
            logger.warning("Camera preview feature will be disabled")

        # Store config for logging
        self.model_file = model_file
        self.min_detection_confidence = min_detection_conf
        self.min_tracking_confidence = min_tracking_conf

        logger.info(
            f"MediaPipe PoseLandmarker initialized (Tasks API): model={model_file}, "
            f"detection_conf={min_detection_conf}, tracking_conf={min_tracking_conf}"
        )

    def _resolve_model_path(self, model_file: str) -> Path:
        """
        Resolve model file path relative to app/cv/models/ directory.

        Args:
            model_file: Model filename (e.g., 'pose_landmarker_full.task')

        Returns:
            Absolute Path to model file

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        # Get app/cv directory (where detection.py lives)
        cv_dir = Path(__file__).parent
        model_dir = cv_dir / 'models'
        model_path = model_dir / model_file

        if not model_path.exists():
            raise FileNotFoundError(
                f"MediaPipe model file not found: {model_path}\n"
                f"Download from: https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
                f"pose_landmarker_full/float16/latest/pose_landmarker_full.task\n"
                f"Place in: {model_dir}/"
            )

        return model_path

    def detect_landmarks(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect pose landmarks in video frame using Tasks API (Story 8.2).

        Args:
            frame: BGR image from OpenCV (np.ndarray, shape (H, W, 3), dtype uint8)

        Returns:
            dict: {
                'landmarks': List of NormalizedLandmark objects or None,
                'user_present': bool (True if person detected, False if away),
                'confidence': float (0.0-1.0, based on nose landmark visibility)
            }

        **Implementation Details:**
        - Converts BGR to RGB (MediaPipe expects RGB)
        - Uses detect_for_video() with timestamp (Tasks API requirement)
        - Extracts nose landmark for confidence scoring
        - Returns user_present=False when no person detected
        - Thread-safe via GIL protection
        """
        if frame is None:
            logger.warning("Received None frame for pose detection")
            return {
                'landmarks': None,
                'user_present': False,
                'confidence': 0.0
            }

        # Convert BGR (OpenCV) to RGB (MediaPipe)
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except cv2.error as e:
            logger.error(
                f"Frame conversion failed: {e}, "
                f"frame shape={frame.shape if hasattr(frame, 'shape') else 'N/A'}, "
                f"dtype={frame.dtype if hasattr(frame, 'dtype') else 'N/A'}"
            )
            return {
                'landmarks': None,
                'user_present': False,
                'confidence': 0.0
            }

        # Create MediaPipe Image object (Tasks API requirement)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Generate timestamp for VIDEO mode (required by Tasks API)
        # Assumes 10 FPS = 100ms per frame
        timestamp_ms = int(self.frame_counter * 100)
        self.frame_counter += 1

        # Detect pose landmarks using Tasks API
        results = self.landmarker.detect_for_video(mp_image, timestamp_ms)

        # Check if pose detected (user present in frame)
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            # Extract first person's landmarks (num_poses=1)
            # Tasks API returns NormalizedLandmarkList, which is directly indexable
            landmarks = results.pose_landmarks[0]

            # Extract confidence score from nose landmark (most stable landmark)
            # Landmark structure: landmarks is directly indexable list of NormalizedLandmark objects
            nose_landmark = landmarks[0]  # Index 0 = NOSE (same as legacy API)
            confidence = nose_landmark.visibility

            logger.debug(f"Pose detected: confidence={confidence:.2f}")

            return {
                'landmarks': landmarks,  # List of NormalizedLandmark objects
                'user_present': True,
                'confidence': confidence
            }
        else:
            logger.debug("No pose detected: user absent")
            return {
                'landmarks': None,
                'user_present': False,
                'confidence': 0.0
            }

    def draw_landmarks(
        self,
        frame: np.ndarray,
        landmarks: Optional[Any],
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> np.ndarray:
        """
        Draw pose landmarks on frame for visualization (FR4).

        IMPORTANT: This method modifies the frame in-place and returns a reference
        to the same frame object. If you need to preserve the original frame,
        create a copy before calling this method.

        Args:
            frame: BGR image from OpenCV (np.ndarray, shape (H, W, 3), dtype uint8)
            landmarks: MediaPipe pose landmarks (list of NormalizedLandmark) or None
            color: BGR color tuple (default green for good posture)

        Returns:
            np.ndarray: Reference to the modified frame with landmarks drawn
                       (or original frame unchanged if no landmarks)
        """
        if landmarks is None or frame is None:
            return frame

        # Check if drawing utilities are available
        if self.mp_drawing is None or self.mp_pose is None:
            logger.debug("Drawing utilities not available - skipping landmark visualization")
            return frame

        # Convert landmarks list to proto for drawing utilities
        # Tasks API returns list, but drawing utils expect NormalizedLandmarkList proto
        from mediapipe.framework.formats import landmark_pb2

        landmark_proto = landmark_pb2.NormalizedLandmarkList()
        for lm in landmarks:
            landmark_proto.landmark.add(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=lm.visibility,
                presence=lm.presence
            )

        # Draw skeleton overlay with configurable color
        self.mp_drawing.draw_landmarks(
            frame,
            landmark_proto,
            self.mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=self.mp_drawing.DrawingSpec(
                color=color,
                thickness=2,
                circle_radius=2
            ),
            connection_drawing_spec=self.mp_drawing.DrawingSpec(
                color=color,
                thickness=2
            )
        )

        return frame

    def close(self):
        """Release MediaPipe PoseLandmarker resources."""
        if hasattr(self, 'landmarker') and self.landmarker:
            self.landmarker.close()
            logger.info("MediaPipe PoseLandmarker resources released")
