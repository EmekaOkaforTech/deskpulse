"""
Windows Camera Capture Module for Standalone Edition.

Uses OpenCV with MSMF/DirectShow backends to capture from Windows webcams.
Supports built-in and USB cameras with enhanced enumeration and hot-plug detection.
"""

import cv2
import logging
from typing import Optional, Tuple, List, Dict
import numpy as np
import threading
import time

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
        self._lock = threading.Lock()  # Protect self.cap access from threads

        logger.info(f"WindowsCamera initialized: index={camera_index}, "
                   f"fps={fps}, resolution={width}x{height}")

    def open(self) -> bool:
        """
        Open camera with MSMF backend and DirectShow fallback.

        Handles MSMF slow initialization (5-30 seconds) with:
        - Async initialization in background thread
        - User feedback during long waits
        - 35-second timeout
        - DirectShow fallback

        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        logger.info("Opening camera with MSMF backend (may take 5-30 seconds)...")

        # Result container for thread communication
        result = {
            'success': False,
            'backend': None,
            'error': None,
            'completed': threading.Event()
        }

        def _open_msmf():
            """Try MSMF backend in background thread."""
            try:
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_MSMF)
                if cap.isOpened():
                    # Verify camera works by reading frame
                    ret, _ = cap.read()
                    if ret:
                        # Thread-safe assignment to self.cap
                        with self._lock:
                            self.cap = cap
                        result['success'] = True
                        result['backend'] = 'MSMF'
                    else:
                        cap.release()
                        result['error'] = "MSMF: Camera opened but read failed"
            except Exception as e:
                result['error'] = f"MSMF exception: {e}"
            finally:
                result['completed'].set()

        # Open in background thread with timeout
        thread = threading.Thread(target=_open_msmf, daemon=True)
        thread.start()

        # Wait up to 35 seconds with progress feedback
        for elapsed in range(0, 36):
            if result['completed'].wait(timeout=1.0):
                break
            if elapsed > 0 and elapsed % 5 == 0:
                logger.info(f"Still opening camera... ({elapsed}s elapsed)")

        if result['success']:
            logger.info("Camera opened with MSMF backend")
            self._configure_camera_properties()
            self._warmup_camera()
            self.is_opened = True
            return True

        # MSMF failed or timed out - try DirectShow fallback
        logger.warning(f"MSMF failed/timed out: {result.get('error', 'timeout')}, trying DirectShow...")

        try:
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)

            if cap.isOpened():
                # Verify camera works
                ret, _ = cap.read()
                if ret:
                    # Thread-safe assignment
                    with self._lock:
                        self.cap = cap
                    logger.info("Camera opened with DirectShow backend")
                    self._configure_camera_properties()
                    self._warmup_camera()
                    self.is_opened = True
                    return True
                else:
                    logger.error("DirectShow: Camera opened but read failed")
                    cap.release()
                    return False
            else:
                logger.error(f"Failed to open camera at index {self.camera_index}")
                return False

        except Exception as e:
            logger.exception(f"Error opening camera with DirectShow: {e}")
            return False

    def _configure_camera_properties(self):
        """
        Configure camera properties with codec fallback.

        Sets:
        - Buffer size to 1 for low latency
        - MJPEG codec (with YUYV fallback if unsupported)
        - Resolution and FPS
        """
        if not self.cap:
            return

        # Set buffer size to 1 for low latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Try MJPEG codec first (better performance)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

        # Check if MJPEG worked
        actual_fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        mjpeg_fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')

        if actual_fourcc != mjpeg_fourcc:
            logger.warning("MJPEG codec not supported, trying YUYV...")
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))

            # Verify YUYV worked
            actual_fourcc = int(self.cap.get(cv2.CAP_PROP_FOURCC))
            yuyv_fourcc = cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V')

            if actual_fourcc == yuyv_fourcc:
                logger.info(f"Using codec: YUYV (fourcc={actual_fourcc})")
            elif actual_fourcc == 0:
                logger.warning("Codec could not be set, using camera default")
            else:
                logger.info(f"Using codec: Unknown (fourcc={actual_fourcc})")
        else:
            logger.info("Using codec: MJPEG")

        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        # Set FPS (not all cameras support this)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        # Verify settings
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        logger.info(f"Camera configured: resolution={actual_width}x{actual_height}, "
                   f"fps={actual_fps}, buffer_size=1")

    def _warmup_camera(self):
        """
        Discard first 2 frames (camera warmup).

        Prevents corrupted/black frames on initial camera open.
        Common issue with many cameras.
        """
        if not self.cap:
            return

        logger.debug("Warming up camera (discarding first 2 frames)...")

        for i in range(2):
            ret, _ = self.cap.read()
            if not ret:
                logger.warning(f"Failed to read warmup frame {i+1}/2")

        logger.debug("Camera warmup complete")

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

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Alias for read() - compatibility with CVPipeline interface.

        Returns:
            Tuple[bool, Optional[np.ndarray]]: (success, frame)
        """
        return self.read()

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


def detect_cameras(backend=cv2.CAP_MSMF) -> List[int]:
    """
    Detect available cameras on Windows using specified backend.

    Args:
        backend: OpenCV backend (CAP_MSMF or CAP_DSHOW)

    Returns:
        List[int]: List of camera indices that are available

    Tests camera indices 0-9 to find working cameras.
    Proven detection method from Story 8.1 - extended to 0-9.
    """
    available_cameras = []

    backend_name = "MSMF" if backend == cv2.CAP_MSMF else "DirectShow"
    logger.info(f"Detecting available cameras with {backend_name} backend...")

    for index in range(10):  # Test indices 0-9 (extended from Story 8.1)
        cap = cv2.VideoCapture(index, backend)

        if cap.isOpened():
            # Try to read a frame to verify camera actually works
            ret, _ = cap.read()
            if ret:
                available_cameras.append(index)
                logger.info(f"Camera found at index {index} (backend: {backend_name})")
            else:
                logger.debug(f"Camera at index {index} opened but failed to read")

            cap.release()

    if not available_cameras:
        logger.warning(f"No cameras detected with {backend_name} backend")
    else:
        logger.info(f"Found {len(available_cameras)} camera(s) with {backend_name}: {available_cameras}")

    return available_cameras


def detect_cameras_with_names() -> List[Dict[str, any]]:
    """
    Detect cameras with enhanced names using cv2-enumerate-cameras (OPTIONAL).

    Returns:
        List[Dict]: List of camera info dicts with keys:
            - index: int (camera index)
            - name: str (friendly name if available, else "Camera N")
            - backend: str (MSMF or DirectShow)
            - vid: str (vendor ID if available, else "unknown")
            - pid: str (product ID if available, else "unknown")

    This function tries to use cv2-enumerate-cameras for enhanced names.
    If that fails, falls back to proven detection from Story 8.1.

    Enterprise-grade: MUST work without cv2-enumerate-cameras package.
    """
    cameras = []

    # Try enhanced detection with cv2-enumerate-cameras (OPTIONAL)
    try:
        from cv2_enumerate_cameras import enumerate_cameras

        logger.info("Attempting enhanced camera detection with cv2-enumerate-cameras...")

        # Try MSMF first (Windows 11 standard)
        try:
            camera_list = enumerate_cameras(cv2.CAP_MSMF)
            backend = "MSMF"
            logger.info(f"Enhanced detection found {len(camera_list)} cameras with MSMF")
        except Exception as e:
            logger.warning(f"MSMF enumeration failed: {e}, trying DirectShow...")
            camera_list = enumerate_cameras(cv2.CAP_DSHOW)
            backend = "DirectShow"
            logger.info(f"Enhanced detection found {len(camera_list)} cameras with DirectShow")

        # Convert to our format
        for cam in camera_list:
            cameras.append({
                'index': cam.index,
                'name': cam.name or f"Camera {cam.index}",
                'backend': backend,
                'vid': getattr(cam, 'vid', 'unknown'),
                'pid': getattr(cam, 'pid', 'unknown')
            })

        logger.info(f"Enhanced detection successful: {len(cameras)} camera(s)")
        return cameras

    except ImportError:
        logger.info("cv2-enumerate-cameras not available, using fallback detection")
    except Exception as e:
        logger.warning(f"Enhanced camera detection failed: {e}, using fallback detection")

    # Fallback to proven basic detection (ALWAYS WORKS)
    logger.info("Using proven basic camera detection (Story 8.1 method)...")

    # Try MSMF first
    indices = detect_cameras(backend=cv2.CAP_MSMF)
    backend = "MSMF"

    # Fall back to DirectShow if MSMF finds nothing
    if not indices:
        logger.info("MSMF found no cameras, trying DirectShow...")
        indices = detect_cameras(backend=cv2.CAP_DSHOW)
        backend = "DirectShow"

    # Convert to our format
    for index in indices:
        cameras.append({
            'index': index,
            'name': f"Camera {index}",  # Basic name
            'backend': backend,
            'vid': 'unknown',
            'pid': 'unknown'
        })

    logger.info(f"Basic detection complete: {len(cameras)} camera(s) found")
    return cameras


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


class CameraHotPlugMonitor:
    """
    Monitor for camera hot-plug events (connect/disconnect).

    Periodically scans for camera changes and notifies listeners.
    Runs in background thread.
    """

    def __init__(self, scan_interval: float = 10.0):
        """
        Initialize hot-plug monitor.

        Args:
            scan_interval: Seconds between camera scans (default 10s)
        """
        self.scan_interval = scan_interval
        self.running = False
        self.thread = None
        self.listeners = []
        self.current_cameras = []

        logger.info(f"CameraHotPlugMonitor initialized (scan interval: {scan_interval}s)")

    def add_listener(self, callback):
        """
        Add listener for camera change events.

        Args:
            callback: Function to call with (added, removed) camera lists
                     Signature: callback(added: List[Dict], removed: List[Dict])
                     Dict format: {'index': int, 'name': str, 'backend': str, ...}
        """
        self.listeners.append(callback)

    def start(self):
        """Start monitoring in background thread."""
        if self.running:
            logger.warning("Hot-plug monitor already running")
            return

        self.running = True
        self.current_cameras = detect_cameras_with_names()  # Use enhanced detection
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

        logger.info(f"Hot-plug monitor started (tracking {len(self.current_cameras)} cameras)")

    def stop(self):
        """Stop monitoring."""
        self.running = False

        if self.thread:
            self.thread.join(timeout=2.0)

        logger.info("Hot-plug monitor stopped")

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.running:
            try:
                time.sleep(self.scan_interval)

                if not self.running:
                    break

                # Scan for cameras with enhanced detection
                new_cameras = detect_cameras_with_names()

                # Get current and new camera indices for comparison
                current_indices = {cam['index'] for cam in self.current_cameras}
                new_indices = {cam['index'] for cam in new_cameras}

                # Detect changes
                added_indices = new_indices - current_indices
                removed_indices = current_indices - new_indices

                if added_indices or removed_indices:
                    # Get full camera info for changed cameras
                    added = [cam for cam in new_cameras if cam['index'] in added_indices]
                    removed = [cam for cam in self.current_cameras if cam['index'] in removed_indices]

                    # Log with camera names
                    added_names = [f"{cam['name']} (index {cam['index']})" for cam in added]
                    removed_names = [f"{cam['name']} (index {cam['index']})" for cam in removed]

                    logger.info(f"Camera change detected - Added: {added_names}, Removed: {removed_names}")

                    # Notify listeners with full camera info
                    for listener in self.listeners:
                        try:
                            listener(added, removed)
                        except Exception as e:
                            logger.exception(f"Hot-plug listener error: {e}")

                    # Update current state
                    self.current_cameras = new_cameras

            except Exception as e:
                logger.exception(f"Hot-plug monitor error: {e}")
                time.sleep(1.0)  # Brief pause on error


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
