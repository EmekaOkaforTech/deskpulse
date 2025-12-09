"""
Unit tests for camera capture module.

Tests cover CameraCapture class with mocked cv2 for isolation.
"""

import logging
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from app.cv.capture import CameraCapture, get_resolution_dimensions
from app.cv.detection import PoseDetector


class TestResolutionDimensions:
    """Test resolution preset conversion."""

    def test_resolution_480p(self):
        """Test 480p resolution mapping."""
        width, height = get_resolution_dimensions('480p')
        assert width == 640
        assert height == 480

    def test_resolution_720p(self):
        """Test 720p resolution mapping."""
        width, height = get_resolution_dimensions('720p')
        assert width == 1280
        assert height == 720

    def test_resolution_1080p(self):
        """Test 1080p resolution mapping."""
        width, height = get_resolution_dimensions('1080p')
        assert width == 1920
        assert height == 1080

    def test_resolution_default(self):
        """Test default resolution for unknown preset."""
        width, height = get_resolution_dimensions('invalid')
        assert width == 640
        assert height == 480


class TestCameraCapture:
    """Test suite for CameraCapture class."""

    @patch('app.cv.capture.cv2')
    def test_camera_initialize_success(self, mock_cv2, app):
        """Test successful camera initialization."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (True, None)  # Warmup frames
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200  # Mock constant

            camera = CameraCapture()
            result = camera.initialize()

            assert result is True
            assert camera.is_active is True
            mock_cv2.VideoCapture.assert_called_with(0, 200)

    @patch('app.cv.capture.cv2')
    def test_camera_initialize_failure(self, mock_cv2, app):
        """Test camera initialization failure."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = False
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            camera = CameraCapture()
            result = camera.initialize()

            assert result is False
            assert camera.is_active is False

    @patch('app.cv.capture.cv2')
    def test_read_frame_success(self, mock_cv2, app):
        """Test successful frame capture."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            # First two calls for warmup, third for actual read
            mock_cap.read.side_effect = [(True, None), (True, None), (True, mock_frame)]
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            camera = CameraCapture()
            camera.initialize()
            success, frame = camera.read_frame()

            assert success is True
            assert frame is not None
            assert frame.shape == (720, 1280, 3)

    @patch('app.cv.capture.cv2')
    def test_read_frame_inactive(self, mock_cv2, app):
        """Test read_frame returns False when camera inactive."""
        with app.app_context():
            camera = CameraCapture()
            success, frame = camera.read_frame()

            assert success is False
            assert frame is None

    @patch('app.cv.capture.cv2')
    def test_read_frame_failure(self, mock_cv2, app):
        """Test read_frame handles cv2.read failure."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            # Warmup succeeds, but actual read fails
            mock_cap.read.side_effect = [(True, None), (True, None), (False, None)]
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            camera = CameraCapture()
            camera.initialize()
            success, frame = camera.read_frame()

            assert success is False
            assert frame is None

    @patch('app.cv.capture.cv2')
    def test_context_manager(self, mock_cv2, app):
        """Test context manager support."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (True, None)  # Warmup frames
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            with CameraCapture() as camera:
                assert camera.is_active is True

            mock_cap.release.assert_called_once()

    @patch('app.cv.capture.cv2')
    def test_release(self, mock_cv2, app):
        """Test release method."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (True, None)  # Warmup frames
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            camera = CameraCapture()
            camera.initialize()
            assert camera.is_active is True

            camera.release()
            assert camera.is_active is False
            mock_cap.release.assert_called_once()

    @patch('app.cv.capture.cv2')
    def test_get_actual_fps(self, mock_cv2, app):
        """Test get_actual_fps method."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (True, None)  # Warmup frames
            mock_cap.get.return_value = 10.0
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200
            mock_cv2.CAP_PROP_FPS = 5  # Mock constant

            camera = CameraCapture()
            camera.initialize()
            fps = camera.get_actual_fps()

            assert fps == 10.0
            mock_cap.get.assert_called_with(5)

    @patch('app.cv.capture.cv2')
    def test_get_actual_fps_no_camera(self, mock_cv2, app):
        """Test get_actual_fps returns 0 when camera not initialized."""
        with app.app_context():
            camera = CameraCapture()
            fps = camera.get_actual_fps()
            assert fps == 0

    @patch('app.cv.capture.cv2')
    def test_get_actual_fps_camera_closed(self, mock_cv2, app):
        """Test get_actual_fps returns 0 when camera closed."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = False
            mock_cv2.VideoCapture.return_value = mock_cap

            camera = CameraCapture()
            camera.cap = mock_cap
            fps = camera.get_actual_fps()
            assert fps == 0

    @patch('app.cv.capture.cv2')
    def test_context_manager_init_failure(self, mock_cv2, app):
        """Test context manager raises RuntimeError on init failure."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = False
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            with pytest.raises(RuntimeError, match="Camera initialization failed"):
                with CameraCapture():
                    pass

    @patch('app.cv.capture.cv2')
    def test_warmup_failure(self, mock_cv2, app):
        """Test initialization fails when warmup frames fail."""
        with app.app_context():
            mock_cap = Mock()
            mock_cap.isOpened.return_value = True
            mock_cap.read.return_value = (False, None)  # Warmup fails
            mock_cv2.VideoCapture.return_value = mock_cap
            mock_cv2.CAP_V4L2 = 200

            camera = CameraCapture()
            result = camera.initialize()

            assert result is False
            assert camera.is_active is False
            mock_cap.release.assert_called_once()

    def test_invalid_resolution_warning(self, caplog, app):
        """Test warning logged for invalid resolution preset."""
        with app.app_context():
            with caplog.at_level(logging.WARNING):
                width, height = get_resolution_dimensions('invalid_preset')
                assert width == 640
                assert height == 480
                assert "Invalid resolution 'invalid_preset'" in caplog.text


class TestPoseDetector:
    """Test suite for PoseDetector class."""

    @patch('app.cv.detection.mp')
    def test_pose_detector_initialization(self, mock_mp, app):
        """Test PoseDetector initialization with default config."""
        with app.app_context():
            mock_pose_class = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_class

            detector = PoseDetector()

            assert detector.pose == mock_pose_class
            assert detector.model_complexity == 1
            assert detector.min_detection_confidence == 0.5
            assert detector.min_tracking_confidence == 0.5
            # Verify exact parameters passed to Pose initialization
            mock_mp.solutions.pose.Pose.assert_called_once_with(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                enable_segmentation=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )

    @patch('app.cv.detection.mp')
    @patch('app.cv.detection.cv2')
    def test_detect_landmarks_success(self, mock_cv2, mock_mp, app):
        """Test successful landmark detection with user present."""
        with app.app_context():
            # Setup mocks
            mock_pose_instance = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_instance
            mock_mp.solutions.pose.PoseLandmark.NOSE = 0

            # Mock successful detection
            mock_landmarks = MagicMock()
            mock_nose = MagicMock()
            mock_nose.visibility = 0.87
            mock_landmarks.landmark = [mock_nose]

            mock_results = Mock()
            mock_results.pose_landmarks = mock_landmarks
            mock_pose_instance.process.return_value = mock_results

            # Mock BGR to RGB conversion
            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            mock_cv2.cvtColor.return_value = mock_frame
            mock_cv2.COLOR_BGR2RGB = 4  # Mock constant

            detector = PoseDetector()
            result = detector.detect_landmarks(mock_frame)

            assert result['user_present'] is True
            assert result['landmarks'] is not None
            assert result['confidence'] == 0.87
            mock_cv2.cvtColor.assert_called_once()

    @patch('app.cv.detection.mp')
    @patch('app.cv.detection.cv2')
    def test_detect_landmarks_no_person(self, mock_cv2, mock_mp, app):
        """Test landmark detection when user is absent."""
        with app.app_context():
            mock_pose_instance = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_instance

            # Mock no detection (user away)
            mock_results = Mock()
            mock_results.pose_landmarks = None
            mock_pose_instance.process.return_value = mock_results

            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            mock_cv2.cvtColor.return_value = mock_frame
            mock_cv2.COLOR_BGR2RGB = 4

            detector = PoseDetector()
            result = detector.detect_landmarks(mock_frame)

            assert result['user_present'] is False
            assert result['landmarks'] is None
            assert result['confidence'] == 0.0

    @patch('app.cv.detection.mp')
    @patch('app.cv.detection.cv2')
    def test_detect_landmarks_none_frame(self, mock_cv2, mock_mp, app):
        """Test landmark detection with None frame."""
        with app.app_context():
            mock_pose_instance = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_instance

            detector = PoseDetector()
            result = detector.detect_landmarks(None)

            assert result['user_present'] is False
            assert result['landmarks'] is None
            assert result['confidence'] == 0.0
            mock_cv2.cvtColor.assert_not_called()

    @patch('app.cv.detection.mp')
    def test_draw_landmarks_success(self, mock_mp, app):
        """Test drawing landmarks on frame."""
        with app.app_context():
            mock_pose_instance = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_instance
            mock_mp.solutions.drawing_utils = Mock()

            detector = PoseDetector()

            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            mock_landmarks = Mock()

            result_frame = detector.draw_landmarks(mock_frame, mock_landmarks)

            assert result_frame is not None
            mock_mp.solutions.drawing_utils.draw_landmarks.assert_called_once()

    @patch('app.cv.detection.mp')
    def test_draw_landmarks_none_landmarks(self, mock_mp, app):
        """Test drawing with None landmarks returns original frame."""
        with app.app_context():
            mock_pose_instance = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_instance
            mock_mp.solutions.drawing_utils = Mock()

            detector = PoseDetector()

            mock_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            result_frame = detector.draw_landmarks(mock_frame, None)

            assert result_frame is mock_frame
            mock_mp.solutions.drawing_utils.draw_landmarks.assert_not_called()

    @patch('app.cv.detection.mp')
    def test_close_releases_resources(self, mock_mp, app):
        """Test close() releases MediaPipe resources."""
        with app.app_context():
            mock_pose_instance = Mock()
            mock_mp.solutions.pose.Pose.return_value = mock_pose_instance

            detector = PoseDetector()
            detector.close()

            mock_pose_instance.close.assert_called_once()
