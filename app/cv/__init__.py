"""Computer vision module for DeskPulse posture monitoring."""

from app.cv.capture import CameraCapture, get_resolution_dimensions  # Story 2.1
from app.cv.detection import PoseDetector  # Story 2.2
from app.cv.classification import PostureClassifier  # Story 2.3
from app.cv.pipeline import CVPipeline, cv_queue  # Story 2.4

__all__ = [
    'CameraCapture',
    'get_resolution_dimensions',
    'PoseDetector',
    'PostureClassifier',
    'CVPipeline',
    'cv_queue'
]
