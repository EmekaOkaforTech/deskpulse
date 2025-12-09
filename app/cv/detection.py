"""MediaPipe Pose landmark detection for DeskPulse posture monitoring."""

import cv2
import logging
import numpy as np
from typing import Optional, Dict, Any, Tuple
from flask import current_app

try:
    import mediapipe as mp
except ImportError:
    # MediaPipe not available - will be mocked in tests
    mp = None

logger = logging.getLogger('deskpulse.cv')


class PoseDetector:
    """
    Detects human pose landmarks using MediaPipe Pose.

    Optimized for Raspberry Pi 4/5 hardware with configuration tuned for
    real-time performance (5-10 FPS) while maintaining detection accuracy.

    Attributes:
        mp_pose: MediaPipe Pose solution module
        pose: MediaPipe Pose instance with optimized settings
        mp_drawing: MediaPipe drawing utilities for visualization
        model_complexity: Model variant (0=lite, 1=full, 2=heavy)
        min_detection_confidence: Minimum confidence for initial detection
        min_tracking_confidence: Minimum confidence for landmark tracking
    """

    def __init__(self):
        """Initialize PoseDetector with config from Flask app."""
        if mp is None:
            raise ImportError(
                "MediaPipe is not installed. Install with: pip install mediapipe"
            )
        self.mp_pose = mp.solutions.pose

        # Load configuration from app config (Story 1.3 pattern)
        model_complexity = current_app.config.get('MEDIAPIPE_MODEL_COMPLEXITY', 1)
        min_detection_conf = current_app.config.get(
            'MEDIAPIPE_MIN_DETECTION_CONFIDENCE', 0.5
        )
        min_tracking_conf = current_app.config.get(
            'MEDIAPIPE_MIN_TRACKING_CONFIDENCE', 0.5
        )
        smooth_landmarks = current_app.config.get('MEDIAPIPE_SMOOTH_LANDMARKS', True)

        # Initialize MediaPipe Pose with Pi-optimized settings
        try:
            self.pose = self.mp_pose.Pose(
                static_image_mode=False,            # Video stream mode (not static images)
                model_complexity=model_complexity,  # 1 = full model (optimal for Pi)
                smooth_landmarks=smooth_landmarks,  # Reduce jitter in tracking
                enable_segmentation=False,          # Disable to save ~20% CPU
                min_detection_confidence=min_detection_conf,
                min_tracking_confidence=min_tracking_conf
            )
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe Pose: {e}")
            raise RuntimeError(f"MediaPipe Pose initialization failed: {e}") from e

        self.mp_drawing = mp.solutions.drawing_utils
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_conf
        self.min_tracking_confidence = min_tracking_conf

        logger.info(
            f"MediaPipe Pose initialized: model_complexity={model_complexity}, "
            f"detection_conf={min_detection_conf}, tracking_conf={min_tracking_conf}"
        )

    def detect_landmarks(self, frame: 'np.ndarray') -> Dict[str, Any]:
        """
        Detect pose landmarks in video frame.

        Args:
            frame: BGR image from OpenCV (np.ndarray, shape (H, W, 3), dtype uint8)

        Returns:
            dict: {
                'landmarks': NormalizedLandmarkList or None,
                'user_present': bool (True if person detected, False if away),
                'confidence': float (0.0-1.0, based on nose landmark visibility)
            }
        """
        if frame is None:
            logger.warning("Received None frame for pose detection")
            return {
                'landmarks': None,
                'user_present': False,
                'confidence': 0.0
            }

        # Convert BGR to RGB (MediaPipe expects RGB color space)
        # Note: Allocates new array each frame (~2.7MB for 720p). Acceptable for MVP,
        # monitor memory usage on Pi if optimization needed.
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

        # Process frame through MediaPipe Pose
        results = self.pose.process(rgb_frame)

        if results.pose_landmarks:
            # Extract confidence score from nose landmark (most stable landmark)
            nose_landmark = results.pose_landmarks.landmark[
                self.mp_pose.PoseLandmark.NOSE
            ]
            confidence = nose_landmark.visibility

            logger.debug(f"Pose detected: confidence={confidence:.2f}")

            return {
                'landmarks': results.pose_landmarks,
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
        frame: 'np.ndarray',
        landmarks: Optional[Any],
        color: Tuple[int, int, int] = (0, 255, 0)
    ) -> 'np.ndarray':
        """
        Draw pose landmarks on frame for visualization (FR4).

        IMPORTANT: This method modifies the frame in-place and returns a reference
        to the same frame object. If you need to preserve the original frame,
        create a copy before calling this method.

        Args:
            frame: BGR image from OpenCV (np.ndarray, shape (H, W, 3), dtype uint8)
            landmarks: MediaPipe pose landmarks (NormalizedLandmarkList) or None
            color: BGR color tuple (default green for good posture)

        Returns:
            np.ndarray: Reference to the modified frame with landmarks drawn
                       (or original frame unchanged if no landmarks)
        """
        if landmarks is None or frame is None:
            return frame

        # Draw skeleton overlay with configurable color
        self.mp_drawing.draw_landmarks(
            frame,
            landmarks,
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
        """Release MediaPipe Pose resources."""
        if hasattr(self, 'pose') and self.pose:
            self.pose.close()
            logger.info("MediaPipe Pose resources released")
