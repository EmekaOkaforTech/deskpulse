# File: app/cv/classification.py
# Story 2.3: Posture Classification
# Story 8.2: MediaPipe Tasks API Migration - Landmark Access Pattern Update

import logging
import math
from typing import Optional, Tuple, Any
from app.cv.pose_landmarks import PoseLandmarkIndex

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

    def __init__(self, app=None):
        """
        Initialize PostureClassifier with config from Flask app.

        Args:
            app: Flask application instance (Story 8.1: for background thread context)
        """
        # Load configurable threshold from app config (Story 1.3 pattern)
        # Story 8.1: Use app.config when provided (avoids current_app in background thread)
        if app:
            self.angle_threshold = app.config.get(
                'POSTURE_ANGLE_THRESHOLD',
                self.GOOD_POSTURE_ANGLE_THRESHOLD
            )
        else:
            from flask import current_app
            self.angle_threshold = current_app.config.get(
                'POSTURE_ANGLE_THRESHOLD',
                self.GOOD_POSTURE_ANGLE_THRESHOLD
            )

        # Use explicit landmark constants (enterprise-grade, Tasks API compatible)
        # No dependency on deprecated mp.solutions.pose
        self.landmarks = PoseLandmarkIndex

        logger.info(
            f"PostureClassifier initialized: angle_threshold={self.angle_threshold}° "
            f"(using MediaPipe 33-point pose model)"
        )

    def classify_posture(
        self,
        landmarks: Optional[Any]
    ) -> Optional[str]:
        """
        Classify posture as 'good' or 'bad' based on landmark geometry.

        Algorithm (Enhanced):
        1. Extract shoulder, hip, and nose landmarks
        2. Calculate shoulder-hip angle (detects forward lean)
        3. Calculate nose-shoulder angle (detects downward slouch)
        4. Bad posture if EITHER angle exceeds threshold

        Args:
            landmarks: MediaPipe landmarks (list of NormalizedLandmark from Tasks API) or None

        Returns:
            str: 'good', 'bad', or None (if user absent)

        Technical Notes (Story 8.2):
        - Landmark access updated for Tasks API: landmarks[index.value]
        - Shoulder-hip angle: Detects forward lean (chest toward desk)
        - Nose-shoulder angle: Detects slouching (head/back rounded forward)
        - Combined approach catches both common bad posture types
        - Computation cost: ~0.2ms (still negligible vs 150-200ms MediaPipe)

        Posture Types Detected:
        - Forward lean: Shoulders ahead of hips horizontally
        - Downward slouch: Head/nose forward of shoulders, rounded back
        - Both: Combined forward lean + slouch (worst posture)

        Landmark Visibility:
        - Relies on MediaPipe's min_tracking_confidence=0.5 (Story 2.2)
        - Nose landmark visibility typically high when user present
        """
        if landmarks is None:
            return None  # User absent, no classification possible

        try:
            # Handle both old protobuf format (landmarks.landmark) and new list format
            # Tasks API should return list directly, but handle protobuf for compatibility
            if hasattr(landmarks, 'landmark'):
                # Old Solutions API format: NormalizedLandmarkList protobuf
                landmarks = landmarks.landmark

            # Extract key landmarks using explicit constants
            # Tasks API returns landmarks as indexable list
            # Using self.landmarks (PoseLandmarkIndex) for enterprise-grade clarity
            nose = landmarks[self.landmarks.NOSE]
            left_shoulder = landmarks[self.landmarks.LEFT_SHOULDER]
            right_shoulder = landmarks[self.landmarks.RIGHT_SHOULDER]
            left_hip = landmarks[self.landmarks.LEFT_HIP]
            right_hip = landmarks[self.landmarks.RIGHT_HIP]

            # Calculate midpoint of shoulders (normalized coordinates 0.0-1.0)
            shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

            # Calculate midpoint of hips (normalized coordinates 0.0-1.0)
            hip_x = (left_hip.x + right_hip.x) / 2
            hip_y = (left_hip.y + right_hip.y) / 2

            # === Check 1: Shoulder-Hip Angle (Forward Lean Detection) ===
            # dx: horizontal displacement (positive = shoulders forward of hips)
            # dy: vertical displacement (positive = hips below shoulders, expected)
            # Note: MediaPipe y increases downward, so hip_y > shoulder_y for upright
            shoulder_hip_dx = shoulder_x - hip_x
            shoulder_hip_dy = hip_y - shoulder_y

            # Angle from vertical (0° = perfect upright torso)
            shoulder_hip_angle = math.degrees(
                math.atan2(shoulder_hip_dx, shoulder_hip_dy)
            )

            # === Check 2: Nose-Shoulder Angle (Slouch Detection) ===
            # When slouching, head moves forward and down relative to shoulders
            # dx: horizontal displacement (positive = nose forward of shoulders)
            # dy: vertical displacement (positive = shoulders below nose, expected)
            nose_shoulder_dx = nose.x - shoulder_x
            nose_shoulder_dy = shoulder_y - nose.y

            # Angle from vertical (0° = head directly above shoulders)
            nose_shoulder_angle = math.degrees(
                math.atan2(nose_shoulder_dx, nose_shoulder_dy)
            )

            # === Classification: Bad if EITHER angle exceeds threshold ===
            is_forward_lean = abs(shoulder_hip_angle) > self.angle_threshold
            is_slouching = abs(nose_shoulder_angle) > self.angle_threshold

            if is_forward_lean or is_slouching:
                posture_state = 'bad'
            else:
                posture_state = 'good'

            logger.debug(
                f"Posture classified: {posture_state} "
                f"(shoulder-hip={shoulder_hip_angle:.1f}°, "
                f"nose-shoulder={nose_shoulder_angle:.1f}°, "
                f"threshold={self.angle_threshold}°)"
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
