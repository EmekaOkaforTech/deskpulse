"""Computer vision module for DeskPulse posture monitoring."""

from app.cv.capture import CameraCapture, get_resolution_dimensions
from app.cv.detection import PoseDetector  # Story 2.2

__all__ = ['CameraCapture', 'get_resolution_dimensions', 'PoseDetector']
