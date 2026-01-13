"""
MediaPipe Pose Landmark Constants (33-Point Model).

This module defines explicit landmark indices for MediaPipe's Pose Landmarker.
These indices are part of MediaPipe's stable API specification and are guaranteed
not to change across versions.

Why explicit constants instead of mp.solutions.pose?
- MediaPipe Tasks API (current standard) doesn't include Solutions API
- Solutions API is deprecated and not bundled in production deployments
- Explicit constants are MORE enterprise-grade than optional imports
- Self-documenting code improves maintainability

Reference: https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
"""


class PoseLandmarkIndex:
    """
    MediaPipe Pose Landmark indices for the 33-point pose model.

    Landmark Coordinate System:
    - X: Horizontal position (0.0 = left edge, 1.0 = right edge)
    - Y: Vertical position (0.0 = top edge, 1.0 = bottom edge)
    - Z: Depth relative to hips (negative = closer to camera)

    All coordinates are normalized to image dimensions.
    """

    # Face landmarks (0-10)
    NOSE = 0
    LEFT_EYE_INNER = 1
    LEFT_EYE = 2
    LEFT_EYE_OUTER = 3
    RIGHT_EYE_INNER = 4
    RIGHT_EYE = 5
    RIGHT_EYE_OUTER = 6
    LEFT_EAR = 7
    RIGHT_EAR = 8
    MOUTH_LEFT = 9
    MOUTH_RIGHT = 10

    # Upper body landmarks (11-16)
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16

    # Hand landmarks (17-22)
    LEFT_PINKY = 17
    RIGHT_PINKY = 18
    LEFT_INDEX = 19
    RIGHT_INDEX = 20
    LEFT_THUMB = 21
    RIGHT_THUMB = 22

    # Lower body landmarks (23-32)
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32

    # Landmark groups for common operations
    SHOULDERS = [LEFT_SHOULDER, RIGHT_SHOULDER]
    HIPS = [LEFT_HIP, RIGHT_HIP]
    POSTURE_KEYPOINTS = [NOSE, LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]

    @classmethod
    def get_landmark_name(cls, index: int) -> str:
        """
        Get human-readable name for landmark index.

        Args:
            index: Landmark index (0-32)

        Returns:
            str: Landmark name (e.g., "NOSE", "LEFT_SHOULDER")

        Raises:
            ValueError: If index is out of range
        """
        if not 0 <= index <= 32:
            raise ValueError(f"Landmark index must be 0-32, got {index}")

        # Build reverse lookup dict
        for name, value in vars(cls).items():
            if isinstance(value, int) and value == index:
                return name

        return f"UNKNOWN_{index}"

    @classmethod
    def validate_landmarks(cls, landmarks) -> bool:
        """
        Validate that landmarks list has correct length.

        Args:
            landmarks: List of landmark objects

        Returns:
            bool: True if landmarks list is valid
        """
        return landmarks is not None and len(landmarks) == 33


# Backward compatibility alias (for migration from Solutions API)
PoseLandmark = PoseLandmarkIndex
