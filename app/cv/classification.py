# File: app/cv/classification.py
import logging
import math
from typing import Optional, Tuple, Any

try:
    import mediapipe as mp
except ImportError:
    # MediaPipe not available - will be mocked in tests
    mp = None

logger = logging.getLogger('deskpulse.cv')


class PostureClassifier:
    """
    Classifies posture as good/bad based on landmark geometry.

    Uses simple shoulder-hip angle calculation to detect forward lean.
    Optimized for Raspberry Pi with minimal computation overhead.

    Attributes:
        GOOD_POSTURE_ANGLE_THRESHOLD: Maximum angle (degrees) from vertical
            for good posture. Default 15° based on ergonomic research.
        angle_threshold: Configurable threshold loaded from Flask config
    """

    # Architecture constant: Good posture threshold (degrees from vertical)
    GOOD_POSTURE_ANGLE_THRESHOLD = 15

    def __init__(self):
        """Initialize PostureClassifier with config from Flask app."""
        from flask import current_app

        # Load configurable threshold from app config (Story 1.3 pattern)
        self.angle_threshold = current_app.config.get(
            'POSTURE_ANGLE_THRESHOLD',
            self.GOOD_POSTURE_ANGLE_THRESHOLD
        )

        # MediaPipe Pose solution for landmark constants
        if mp:
            self.mp_pose = mp.solutions.pose
        else:
            # Mock for tests - landmark indices hardcoded
            self.mp_pose = None

        logger.info(
            f"PostureClassifier initialized: angle_threshold={self.angle_threshold}°"
        )

    def classify_posture(
        self,
        landmarks: Optional[Any]
    ) -> Optional[str]:
        """
        Classify posture as 'good' or 'bad' based on landmark geometry.

        Algorithm:
        1. Extract shoulder and hip landmarks (left/right pairs)
        2. Calculate midpoint of shoulders and hips
        3. Compute angle from vertical using atan2
        4. Compare to threshold (default 15°)

        Args:
            landmarks: MediaPipe NormalizedLandmarkList or None

        Returns:
            str: 'good', 'bad', or None (if user absent)

        Technical Notes:
        - Angle > threshold indicates forward lean (bad posture)
        - Absolute value handles both forward and backward lean
        - None return indicates user absent (no landmarks detected)
        - Computation cost: ~0.1ms (negligible vs 150-200ms MediaPipe)

        Landmark Visibility:
        - MediaPipe provides visibility scores (0.0-1.0) for each landmark
        - Current algorithm uses landmarks regardless of individual visibility
        - Relies on MediaPipe's min_tracking_confidence=0.5 (Story 2.2) to filter
          unreliable detections at the source
        - If future testing reveals accuracy issues, consider checking shoulder/hip
          visibility scores explicitly before classification
        """
        if landmarks is None:
            return None  # User absent, no classification possible

        try:
            # Extract key landmarks using MediaPipe indices
            # Landmark 11: LEFT_SHOULDER
            # Landmark 12: RIGHT_SHOULDER
            # Landmark 23: LEFT_HIP
            # Landmark 24: RIGHT_HIP
            if self.mp_pose:
                left_shoulder = landmarks.landmark[
                    self.mp_pose.PoseLandmark.LEFT_SHOULDER
                ]
                right_shoulder = landmarks.landmark[
                    self.mp_pose.PoseLandmark.RIGHT_SHOULDER
                ]
                left_hip = landmarks.landmark[
                    self.mp_pose.PoseLandmark.LEFT_HIP
                ]
                right_hip = landmarks.landmark[
                    self.mp_pose.PoseLandmark.RIGHT_HIP
                ]
            else:
                # Fallback for tests with mock landmarks
                left_shoulder = landmarks.landmark[11]
                right_shoulder = landmarks.landmark[12]
                left_hip = landmarks.landmark[23]
                right_hip = landmarks.landmark[24]

            # Calculate midpoint of shoulders (normalized coordinates 0.0-1.0)
            shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

            # Calculate midpoint of hips (normalized coordinates 0.0-1.0)
            hip_x = (left_hip.x + right_hip.x) / 2
            hip_y = (left_hip.y + right_hip.y) / 2

            # Calculate angle from vertical (0° = perfect upright)
            # dx: horizontal displacement (positive = shoulders forward of hips)
            # dy: vertical displacement (positive = hips below shoulders, expected)
            # Note: MediaPipe y increases downward, so hip_y > shoulder_y for upright
            dx = shoulder_x - hip_x
            dy = hip_y - shoulder_y

            # Angle in degrees (positive = leaning forward)
            # atan2(dx, dy) gives angle from vertical axis
            angle = math.degrees(math.atan2(dx, dy))

            # Classify based on threshold
            if abs(angle) <= self.angle_threshold:
                posture_state = 'good'
            else:
                posture_state = 'bad'

            logger.debug(
                f"Posture classified: {posture_state} "
                f"(angle={angle:.1f}°, threshold={self.angle_threshold}°)"
            )

            return posture_state

        except (AttributeError, IndexError, TypeError) as e:
            # Handle cases where landmarks are malformed or missing
            logger.warning(f"Posture classification failed: {e}")
            return None

    def get_landmark_color(
        self,
        posture_state: Optional[str]
    ) -> Tuple[int, int, int]:
        """
        Get skeleton overlay color based on posture state (UX integration).

        Color palette is colorblind-safe and follows UX Design guidelines:
        - Green for good posture (positive reinforcement)
        - Amber for bad posture (NOT red - less stressful, "gently persistent")
        - Gray for user absent (neutral, monitoring paused)

        Args:
            posture_state: 'good', 'bad', or None

        Returns:
            tuple: BGR color for OpenCV drawing (Blue, Green, Red order)

        UX Design Rationale:
        - Amber vs red: Reduces anxiety and shame (UX Design: "gently persistent")
        - Colorblind-safe: Green/amber distinguishable by most types of colorblindness
        - Consistent with traffic light metaphor (but amber instead of red)
        """
        if posture_state == 'good':
            return (0, 255, 0)  # Green (RGB: 0, 255, 0)
        elif posture_state == 'bad':
            return (0, 191, 255)  # Amber (RGB: 255, 191, 0) - BGR in OpenCV
        else:
            return (128, 128, 128)  # Gray (RGB: 128, 128, 128) - user absent
