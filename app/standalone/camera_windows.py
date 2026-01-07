"""
Windows Camera Capture Module for Standalone Edition.

Uses OpenCV with DirectShow backend to capture from Windows webcams.
Supports built-in and USB cameras.
"""

import cv2
import logging
from typing import Optional, Tuple, List
import numpy as np

logger = logging.getLogger('deskpulse.standalone.camera')


class WindowsCamera:
    """
    Windows webcam capture using OpenCV DirectShow backend.

    Supports:
    - Built-in laptop webcams
    - USB webcams
    - Multiple camera selection
    - Automatic fallback to available cameras
    """

    def __init__(self, camera_index: int = 0, fps: int = 10,
                 width: int = 640, height: int = 480):
        """
        Initialize Windows camera.

        Args:
            camera_index: Camera device index (0 = default)
            fps: Target frames per second
            width: Frame width in pixels
            height: Frame height in pixels
        """
        self.camera_index = camera_index
        self.fps = fps
        self.width = width
        self.height = height
        self.cap = None
        self.is_opened = False

        logger.info(f"WindowsCamera initialized: index={camera_index}, "
                   f"fps={fps}, resolution={width}x{height}")

    def open(self) -> bool:
        """
        Open camera with DirectShow backend.

        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        try:
            # Use DirectShow backend for Windows
            # CAP_DSHOW = 700 (DirectShow backend constant)
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

            if not self.cap.isOpened():
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False

            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            # Set FPS (not all cameras support this)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)

            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))

            logger.info(f"Camera opened: resolution={actual_width}x{actual_height}, "
                       f"fps={actual_fps}")

            self.is_opened = True
            return True

        except Exception as e:
            logger.exception(f"Error opening camera: {e}")
            return False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read frame from camera.

        Returns:
            Tuple[bool, Optional[np.ndarray]]: (success, frame)
                success: True if frame read successfully
                frame: BGR image as numpy array, or None if failed
        """
        if not self.is_opened or self.cap is None:
            return False, None

        try:
            ret, frame = self.cap.read()

            if not ret:
                logger.warning("Failed to read frame from camera")
                return False, None

            return True, frame

        except Exception as e:
            logger.exception(f"Error reading frame: {e}")
            return False, None

    def release(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            logger.info("Camera released")

        self.is_opened = False

    def is_available(self) -> bool:
        """Check if camera is available and opened."""
        return self.is_opened and self.cap is not None and self.cap.isOpened()

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def detect_cameras() -> List[int]:
    """
    Detect available cameras on Windows.

    Returns:
        List[int]: List of camera indices that are available

    Tests camera indices 0-5 to find working cameras.
    """
    available_cameras = []

    logger.info("Detecting available cameras...")

    for index in range(6):  # Test indices 0-5
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)

        if cap.isOpened():
            # Try to read a frame to verify camera actually works
            ret, _ = cap.read()
            if ret:
                available_cameras.append(index)
                logger.info(f"Camera found at index {index}")
            else:
                logger.debug(f"Camera at index {index} opened but failed to read")

            cap.release()

    if not available_cameras:
        logger.warning("No cameras detected")
    else:
        logger.info(f"Found {len(available_cameras)} camera(s): {available_cameras}")

    return available_cameras


def get_camera_name(index: int) -> str:
    """
    Get camera name (limited on Windows without additional libraries).

    Args:
        index: Camera index

    Returns:
        str: Generic camera name

    Note: DirectShow doesn't provide easy camera name access.
    Would need pygrabber or Windows Media Foundation for real names.
    """
    return f"Camera {index}"


def test_camera(index: int = 0, duration_seconds: int = 5) -> bool:
    """
    Test camera by capturing frames for specified duration.

    Args:
        index: Camera index to test
        duration_seconds: How long to capture frames

    Returns:
        bool: True if camera works correctly, False otherwise
    """
    logger.info(f"Testing camera {index} for {duration_seconds} seconds...")

    try:
        with WindowsCamera(index) as camera:
            if not camera.is_available():
                logger.error(f"Camera {index} not available")
                return False

            import time
            start_time = time.time()
            frame_count = 0

            while time.time() - start_time < duration_seconds:
                ret, frame = camera.read()

                if ret:
                    frame_count += 1
                else:
                    logger.error("Failed to read frame during test")
                    return False

                time.sleep(0.1)  # 10 FPS for testing

            elapsed = time.time() - start_time
            actual_fps = frame_count / elapsed

            logger.info(f"Camera test passed: {frame_count} frames in {elapsed:.2f}s "
                       f"({actual_fps:.1f} FPS)")
            return True

    except Exception as e:
        logger.exception(f"Camera test failed: {e}")
        return False


if __name__ == '__main__':
    # Test camera functionality
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(name)s - %(message)s'
    )

    print("DeskPulse Windows Camera Test")
    print("=" * 50)

    # Detect cameras
    print("\n1. Detecting cameras...")
    cameras = detect_cameras()

    if not cameras:
        print("ERROR: No cameras found!")
        exit(1)

    print(f"\nFound {len(cameras)} camera(s): {cameras}")

    # Test first camera
    print(f"\n2. Testing camera {cameras[0]}...")
    if test_camera(cameras[0], duration_seconds=3):
        print("✓ Camera test passed!")
    else:
        print("✗ Camera test failed!")
        exit(1)

    # Capture single frame
    print(f"\n3. Capturing single frame...")
    with WindowsCamera(cameras[0]) as cam:
        ret, frame = cam.read()

        if ret and frame is not None:
            print(f"✓ Frame captured: shape={frame.shape}, dtype={frame.dtype}")
        else:
            print("✗ Failed to capture frame")
            exit(1)

    print("\n" + "=" * 50)
    print("All tests passed! Camera is working correctly.")
