"""
Camera capture module using OpenCV VideoCapture.

This module provides frame capture from USB webcams with configurable
resolution and FPS targeting for Raspberry Pi 4/5 hardware.
"""

import cv2
import logging
from flask import current_app

logger = logging.getLogger('deskpulse.cv')


def get_resolution_dimensions(resolution: str) -> tuple[int, int]:
    """
    Convert resolution preset to (width, height) dimensions.

    Args:
        resolution: Resolution preset string ('480p', '720p', or '1080p')

    Returns:
        Tuple of (width, height) in pixels
    """
    resolution_map = {
        '480p': (640, 480),
        '720p': (1280, 720),
        '1080p': (1920, 1080)
    }
    if resolution not in resolution_map:
        logger.warning(f"Invalid resolution '{resolution}', defaulting to 480p")
    return resolution_map.get(resolution, (640, 480))  # Default to 480p


class CameraCapture:
    """
    Handles USB camera capture with OpenCV VideoCapture.

    This class wraps cv2.VideoCapture and provides optimized settings
    for Raspberry Pi 4/5 hardware with configurable resolution (480p/720p/1080p)
    targeting 5-10 FPS for real-time posture monitoring.

    Attributes:
        camera_device (int): Camera device index (default: 0 for /dev/video0)
        fps_target (int): Target FPS from config (default: 10)
        resolution (str): Resolution preset from config (default: '720p')
        cap (cv2.VideoCapture): OpenCV video capture object
        is_active (bool): Camera active status flag
    """

    def __init__(self):
        """Initialize CameraCapture with config from Flask app."""
        self.camera_device = current_app.config.get('CAMERA_DEVICE', 0)
        self.fps_target = current_app.config.get('CAMERA_FPS_TARGET', 10)
        self.resolution = current_app.config.get('CAMERA_RESOLUTION', '720p')
        self.cap = None
        self.is_active = False

    def initialize(self) -> bool:
        """
        Initialize camera connection with optimized settings.

        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        try:
            # Use V4L2 backend for Linux/Raspberry Pi compatibility
            self.cap = cv2.VideoCapture(self.camera_device, cv2.CAP_V4L2)

            if not self.cap.isOpened():
                logger.error(f"Camera device {self.camera_device} not found")
                return False

            # Set camera properties from config
            width, height = get_resolution_dimensions(self.resolution)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps_target)

            # Camera warmup: discard first 2 frames to prevent corruption
            for _ in range(2):
                ret, _ = self.cap.read()
                if not ret:
                    logger.error("Camera warmup failed - unable to read frames")
                    self.cap.release()
                    return False

            self.is_active = True
            logger.info(f"Camera connected: /dev/video{self.camera_device} at {self.resolution}")
            return True

        except Exception:
            logger.exception("Camera initialization failed")
            return False

    def read_frame(self) -> tuple[bool, 'np.ndarray | None']:
        """
        Read a single frame from camera.

        Returns:
            tuple: (success: bool, frame: np.ndarray or None)
        """
        if not self.is_active or self.cap is None:
            return False, None

        ret, frame = self.cap.read()

        if not ret:
            logger.warning("Failed to read frame from camera")
            return False, None

        return True, frame

    def release(self) -> None:
        """Release camera resources and mark as inactive."""
        if self.cap is not None:
            self.cap.release()
            self.is_active = False
            logger.info("Camera released")

    def get_actual_fps(self) -> float:
        """Get actual FPS from camera (for debugging/validation)."""
        if self.cap and self.cap.isOpened():
            return self.cap.get(cv2.CAP_PROP_FPS)
        return 0

    def __enter__(self) -> 'CameraCapture':
        """Context manager entry - initialize camera."""
        if not self.initialize():
            raise RuntimeError("Camera initialization failed")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - release camera resources."""
        self.release()
