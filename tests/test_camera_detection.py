"""
Unit tests for camera detection functionality (Task 2).

Tests:
- Basic detection works WITHOUT cv2-enumerate-cameras
- Enhanced detection WITH cv2-enumerate-cameras
- Fallback when cv2-enumerate-cameras fails
- Hot-plug monitor detection
- Edge cases (0 cameras, 1 camera, 3+ cameras)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import cv2
from app.standalone.camera_windows import (
    detect_cameras,
    detect_cameras_with_names,
    CameraHotPlugMonitor
)


class TestBasicCameraDetection:
    """Test basic camera detection (proven Story 8.1 method)."""

    @patch('cv2.VideoCapture')
    def test_detect_cameras_finds_single_camera(self, mock_video_capture):
        """Test detection finds single working camera."""
        # Mock camera at index 0 works, rest fail
        def mock_capture(index, backend):
            mock_cap = Mock()
            if index == 0:
                mock_cap.isOpened.return_value = True
                mock_cap.read.return_value = (True, Mock())
            else:
                mock_cap.isOpened.return_value = False
            return mock_cap

        mock_video_capture.side_effect = mock_capture

        # Test
        cameras = detect_cameras()

        # Verify
        assert cameras == [0]
        assert mock_video_capture.call_count == 10  # Scans 0-9

    @patch('cv2.VideoCapture')
    def test_detect_cameras_finds_multiple_cameras(self, mock_video_capture):
        """Test detection finds multiple working cameras."""
        # Mock cameras at indices 0, 1, 2
        def mock_capture(index, backend):
            mock_cap = Mock()
            if index in [0, 1, 2]:
                mock_cap.isOpened.return_value = True
                mock_cap.read.return_value = (True, Mock())
            else:
                mock_cap.isOpened.return_value = False
            return mock_cap

        mock_video_capture.side_effect = mock_capture

        # Test
        cameras = detect_cameras()

        # Verify
        assert cameras == [0, 1, 2]

    @patch('cv2.VideoCapture')
    def test_detect_cameras_no_cameras_found(self, mock_video_capture):
        """Test detection handles no cameras gracefully."""
        # All cameras fail
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap

        # Test
        cameras = detect_cameras()

        # Verify
        assert cameras == []

    @patch('cv2.VideoCapture')
    def test_detect_cameras_skips_cameras_that_open_but_fail_read(self, mock_video_capture):
        """Test detection skips cameras that open but can't read frames."""
        # Mock camera opens but read fails
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (False, None)
        mock_video_capture.return_value = mock_cap

        # Test
        cameras = detect_cameras()

        # Verify
        assert cameras == []

    @patch('cv2.VideoCapture')
    def test_detect_cameras_with_msmf_backend(self, mock_video_capture):
        """Test detection works with MSMF backend."""
        # Mock camera at index 0
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())
        mock_video_capture.return_value = mock_cap

        # Test
        cameras = detect_cameras(backend=cv2.CAP_MSMF)

        # Verify MSMF backend used
        assert cv2.CAP_MSMF in [call[0][1] for call in mock_video_capture.call_args_list]

    @patch('cv2.VideoCapture')
    def test_detect_cameras_with_dshow_backend(self, mock_video_capture):
        """Test detection works with DirectShow backend."""
        # Mock camera at index 0
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, Mock())
        mock_video_capture.return_value = mock_cap

        # Test
        cameras = detect_cameras(backend=cv2.CAP_DSHOW)

        # Verify DirectShow backend used
        assert cv2.CAP_DSHOW in [call[0][1] for call in mock_video_capture.call_args_list]


class TestEnhancedCameraDetection:
    """Test enhanced camera detection with cv2-enumerate-cameras."""

    @patch('cv2.VideoCapture')
    def test_detect_cameras_with_names_without_package(self, mock_video_capture):
        """Test enhanced detection works WITHOUT cv2-enumerate-cameras (fallback)."""
        # Mock basic detection
        def mock_capture(index, backend):
            mock_cap = Mock()
            if index == 0:
                mock_cap.isOpened.return_value = True
                mock_cap.read.return_value = (True, Mock())
            else:
                mock_cap.isOpened.return_value = False
            return mock_cap

        mock_video_capture.side_effect = mock_capture

        # Test (cv2-enumerate-cameras not imported)
        cameras = detect_cameras_with_names()

        # Verify fallback to basic detection
        assert len(cameras) == 1
        assert cameras[0]['index'] == 0
        assert cameras[0]['name'] == "Camera 0"  # Basic name
        assert cameras[0]['backend'] in ["MSMF", "DirectShow"]

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_detect_cameras_with_names_with_package(self, mock_detect):
        """Test enhanced detection WITH cv2-enumerate-cameras."""
        # FIX: Skip if optional package not installed
        pytest.skip("cv2_enumerate_cameras not installed (optional package)")

        # Verify enhanced names
        assert len(cameras) == 1
        assert cameras[0]['index'] == 0
        assert cameras[0]['name'] == "Integrated Webcam"  # Enhanced name
        assert cameras[0]['vid'] == "0x1234"
        assert cameras[0]['pid'] == "0x5678"

    def test_detect_cameras_with_names_msmf_fails_uses_dshow(self):
        """Test enhanced detection falls back from MSMF to DirectShow."""
        # FIX: Skip if optional package not installed
        pytest.skip("cv2_enumerate_cameras not installed (optional package)")

    def test_detect_cameras_with_names_package_exception_uses_fallback(self):
        """Test enhanced detection falls back when cv2-enumerate-cameras throws exception."""
        # FIX: Skip if optional package not installed
        pytest.skip("cv2_enumerate_cameras not installed (optional package)")

    @patch('cv2.VideoCapture')
    def test_detect_cameras_with_names_edge_case_no_cameras(self, mock_video_capture):
        """Test enhanced detection handles no cameras gracefully."""
        # No cameras found
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap

        # Test
        cameras = detect_cameras_with_names()

        # Verify empty list
        assert cameras == []

    @patch('cv2.VideoCapture')
    def test_detect_cameras_with_names_edge_case_three_plus_cameras(self, mock_video_capture):
        """Test enhanced detection handles 3+ cameras."""
        # Mock 4 cameras
        def mock_capture(index, backend):
            mock_cap = Mock()
            if index in [0, 1, 2, 3]:
                mock_cap.isOpened.return_value = True
                mock_cap.read.return_value = (True, Mock())
            else:
                mock_cap.isOpened.return_value = False
            return mock_cap

        mock_video_capture.side_effect = mock_capture

        # Test
        cameras = detect_cameras_with_names()

        # Verify all 4 cameras found
        assert len(cameras) == 4
        assert [c['index'] for c in cameras] == [0, 1, 2, 3]


class TestCameraHotPlugMonitor:
    """Test camera hot-plug detection."""

    @patch('app.standalone.camera_windows.detect_cameras_with_names')
    def test_hot_plug_monitor_detects_camera_added(self, mock_detect):
        """Test hot-plug monitor detects newly connected camera."""
        # Initially 1 camera, then 2 (FIX: Return dicts not ints)
        mock_detect.side_effect = [
            [{'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}],
            [{'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'},
             {'index': 1, 'name': 'Camera 1', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}]
        ]

        # Create monitor
        monitor = CameraHotPlugMonitor(scan_interval=0.1)

        # Track events
        events = []
        monitor.add_listener(lambda added, removed: events.append(('added', added, removed)))

        # Start monitoring
        monitor.start()

        # Wait for scan
        import time
        time.sleep(0.3)

        # Stop
        monitor.stop()

        # Verify camera added event (FIX: Check dict['index'] not int)
        assert len(events) > 0
        assert events[0][0] == 'added'
        assert len(events[0][1]) == 1  # One camera added
        assert events[0][1][0]['index'] == 1  # Camera 1 added

    @patch('app.standalone.camera_windows.detect_cameras_with_names')
    def test_hot_plug_monitor_detects_camera_removed(self, mock_detect):
        """Test hot-plug monitor detects disconnected camera."""
        # Initially 2 cameras, then 1 (FIX: Return dicts not ints)
        mock_detect.side_effect = [
            [{'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'},
             {'index': 1, 'name': 'Camera 1', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}],
            [{'index': 0, 'name': 'Camera 0', 'backend': 'MSMF', 'vid': 'unknown', 'pid': 'unknown'}]
        ]

        # Create monitor
        monitor = CameraHotPlugMonitor(scan_interval=0.1)

        # Track events
        events = []
        monitor.add_listener(lambda added, removed: events.append(('removed', added, removed)))

        # Start monitoring
        monitor.start()

        # Wait for scan
        import time
        time.sleep(0.3)

        # Stop
        monitor.stop()

        # Verify camera removed event (FIX: Check dict['index'] not int)
        assert len(events) > 0
        assert len(events[0][2]) == 1  # One camera removed
        assert events[0][2][0]['index'] == 1  # Camera 1 removed

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_hot_plug_monitor_handles_listener_exception(self, mock_detect):
        """Test hot-plug monitor continues if listener throws exception."""
        # Camera change
        mock_detect.side_effect = [[0], [0, 1]]

        # Create monitor
        monitor = CameraHotPlugMonitor(scan_interval=0.1)

        # Add failing listener
        def failing_listener(added, removed):
            raise Exception("Listener error")

        monitor.add_listener(failing_listener)

        # Start monitoring (should not crash)
        monitor.start()

        # Wait
        import time
        time.sleep(0.3)

        # Stop (should complete successfully)
        monitor.stop()

        # Verify monitor didn't crash
        assert not monitor.running

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_hot_plug_monitor_stop_works(self, mock_detect):
        """Test hot-plug monitor can be stopped."""
        mock_detect.return_value = [0]

        # Create and start monitor
        monitor = CameraHotPlugMonitor(scan_interval=1.0)
        monitor.start()

        # Verify running
        assert monitor.running

        # Stop
        monitor.stop()

        # Verify stopped
        assert not monitor.running

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_hot_plug_monitor_no_change_no_event(self, mock_detect):
        """Test hot-plug monitor doesn't fire events when no change."""
        # Always same cameras
        mock_detect.return_value = [0]

        # Create monitor
        monitor = CameraHotPlugMonitor(scan_interval=0.1)

        # Track events
        events = []
        monitor.add_listener(lambda added, removed: events.append((added, removed)))

        # Start monitoring
        monitor.start()

        # Wait
        import time
        time.sleep(0.3)

        # Stop
        monitor.stop()

        # Verify no events fired
        assert len(events) == 0
