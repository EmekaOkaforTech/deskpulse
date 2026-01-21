"""
Camera capture module using OpenCV VideoCapture.

This module provides frame capture from USB webcams with configurable
resolution and FPS targeting for Raspberry Pi 4/5 hardware.
"""

import os
# Disable OBSENSOR backend before importing cv2 (Raspberry Pi fix)
# OBSENSOR is for Orbbec 3D cameras and interferes with USB webcams
os.environ['OPENCV_VIDEOIO_PRIORITY_OBSENSOR'] = '0'

import cv2
import logging
from flask import current_app
from typing import Optional

from app.cv.camera_permissions_linux import check_camera_permissions
from app.cv.camera_error_handler_linux import CameraErrorHandler

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
        error_handler (CameraErrorHandler): Error diagnostics handler
        last_error (dict): Last error details (if any)
    """

    def __init__(self):
        """Initialize CameraCapture with config from Flask app."""
        self.camera_device = current_app.config.get('CAMERA_DEVICE', 0)
        self.fps_target = current_app.config.get('CAMERA_FPS_TARGET', 10)
        self.resolution = current_app.config.get('CAMERA_RESOLUTION', '720p')
        self.cap = None
        self.is_active = False
        self.error_handler = CameraErrorHandler()
        self.last_error: Optional[dict] = None

    def initialize(self) -> bool:
        """
        Initialize camera connection with optimized settings.

        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        try:
            # Pre-check: Verify camera permissions before attempting open
            permissions = check_camera_permissions()
            if not permissions['accessible']:
                self.last_error = self.error_handler.handle_camera_error(
                    self.camera_device if isinstance(self.camera_device, int) else 0
                )
                logger.error(f"Camera permission denied: {permissions['error']}")
                logger.error(f"Solution: {self.last_error['solution']}")
                return False

            # Raspberry Pi workaround: Add small delay before camera access
            import time
            time.sleep(0.5)

            # Use integer device index directly (V4L2 backend requirement)
            # V4L2 on Raspberry Pi does NOT support string paths like "/dev/video0"
            # Must use integer index (0, 1, 2, etc.)
            if isinstance(self.camera_device, str):
                # If string path provided, extract index
                import re
                match = re.search(r'/dev/video(\d+)', self.camera_device)
                device_index = int(match.group(1)) if match else 0
            else:
                device_index = self.camera_device

            logger.info("Attempting to open camera device %d", device_index)

            # Use default backend (V4L2 causes issues on some Raspberry Pi systems)
            # OpenCV will automatically select the best available backend
            self.cap = cv2.VideoCapture(device_index)

            if not self.cap.isOpened():
                # Use error handler for specific diagnostics
                self.last_error = self.error_handler.handle_camera_error(device_index)
                logger.error(f"Camera error: {self.last_error['error_type']} - {self.last_error['message']}")
                logger.error(f"Solution: {self.last_error['solution']}")
                return False

            # Set camera properties from config
            width, height = get_resolution_dimensions(self.resolution)

            # Set FOURCC format to MJPEG for better compatibility
            # Based on: https://forums.raspberrypi.com/viewtopic.php?t=305804
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps_target)

            # Set buffer size to 1 to minimize latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Camera warmup: discard first 2 frames to prevent corruption
            for _ in range(2):
                ret, _ = self.cap.read()
                if not ret:
                    # Use error handler for specific diagnostics
                    self.last_error = self.error_handler.handle_camera_error(device_index)
                    logger.error(f"Camera warmup failed: {self.last_error['error_type']}")
                    logger.error(f"Solution: {self.last_error['solution']}")
                    self.cap.release()
                    return False

            self.is_active = True
            self.last_error = None  # Clear any previous error
            logger.info("Camera connected: device %d at %s", device_index, self.resolution)
            return True

        except Exception as e:
            # Use error handler for exception diagnostics
            device_idx = self.camera_device if isinstance(self.camera_device, int) else 0
            self.last_error = self.error_handler.handle_camera_error(device_idx, exception=e)
            logger.exception(f"Camera initialization failed: {self.last_error['error_type']}")
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

    def get_last_error(self) -> Optional[dict]:
        """
        Get last camera error details.

        Returns:
            dict: Error details with keys:
                - error_type: str (PERMISSION_DENIED, CAMERA_IN_USE, NOT_FOUND, DRIVER_ERROR, UNKNOWN)
                - message: str (user-facing message)
                - solution: str (step-by-step fix instructions)
                - retry_recommended: bool
            Or None if no error occurred.
        """
        return self.last_error

    def __enter__(self) -> 'CameraCapture':
        """Context manager entry - initialize camera."""
        if not self.initialize():
            raise RuntimeError("Camera initialization failed")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - release camera resources."""
        self.release()
