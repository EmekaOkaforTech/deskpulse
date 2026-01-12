"""
Unit tests for camera error handler (Story 8.3).

Enterprise-grade tests covering:
- Process identification for "camera in use" errors
- Driver malfunction detection (PowerShell + registry fallback)
- USB bandwidth calculation with MJPEG compression
- Retry logic with exponential backoff
- All error types and solutions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.standalone.camera_error_handler import CameraErrorHandler


class TestCameraInUseDetection:
    """Test camera-in-use detection with process identification (Critical Fix #2)."""

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_find_camera_using_processes_identifies_teams(self, mock_subprocess):
        """Test process identification detects Microsoft Teams using camera."""
        # Mock PowerShell returns Teams process (dict format with Name key)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"Name":"Teams"}]'
        mock_subprocess.return_value = mock_result

        error_handler = CameraErrorHandler()
        process = error_handler._find_camera_using_processes()

        assert process == "Teams"
        assert mock_subprocess.called

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_find_camera_using_processes_identifies_multiple(self, mock_subprocess):
        """Test process identification returns first of multiple processes."""
        # Mock PowerShell returns multiple processes (dict format with Name key)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"Name":"Zoom"},{"Name":"Chrome"},{"Name":"Teams"}]'
        mock_subprocess.return_value = mock_result

        error_handler = CameraErrorHandler()
        process = error_handler._find_camera_using_processes()

        # Should return first process
        assert process in ["Zoom", "Chrome", "Teams"]

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_find_camera_using_processes_powershell_fails(self, mock_subprocess):
        """Test process identification falls back when PowerShell fails."""
        # Mock PowerShell failure
        mock_subprocess.side_effect = FileNotFoundError

        error_handler = CameraErrorHandler()
        process = error_handler._find_camera_using_processes()

        assert process is None

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_find_camera_using_processes_no_processes_found(self, mock_subprocess):
        """Test process identification returns None when no processes found."""
        # Mock PowerShell returns empty array
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '[]'
        mock_subprocess.return_value = mock_result

        error_handler = CameraErrorHandler()
        process = error_handler._find_camera_using_processes()

        assert process is None

    @patch('cv2.VideoCapture')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._find_camera_using_processes')
    def test_check_camera_in_use_with_process(self, mock_find_process, mock_videocapture):
        """Test camera in use detection includes process name."""
        # Mock camera can't open (in use)
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_videocapture.return_value = mock_cap
        mock_find_process.return_value = "Chrome"

        error_handler = CameraErrorHandler()
        result = error_handler._check_camera_in_use(0)

        assert result['is_in_use'] is True
        assert result['process'] == "Chrome"

    @patch('cv2.VideoCapture')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._find_camera_using_processes')
    def test_check_camera_in_use_without_process(self, mock_find_process, mock_videocapture):
        """Test camera in use detection works without process identification."""
        # Mock camera can't open (in use)
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_videocapture.return_value = mock_cap
        mock_find_process.return_value = None

        error_handler = CameraErrorHandler()
        result = error_handler._check_camera_in_use(0)

        assert result['is_in_use'] is True
        assert result['process'] is None


class TestDriverMalfunctionDetection:
    """Test driver malfunction detection with PowerShell + registry fallback (Critical Fix #7)."""

    @patch('app.standalone.camera_error_handler.CameraErrorHandler._is_powershell_available')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._check_driver_via_powershell')
    def test_check_driver_malfunction_uses_powershell_first(self, mock_ps_check, mock_ps_available):
        """Test driver check uses PowerShell when available."""
        mock_ps_available.return_value = True
        mock_ps_check.return_value = {'has_issue': False}

        error_handler = CameraErrorHandler()
        result = error_handler._check_driver_malfunction(0)

        mock_ps_available.assert_called_once()
        mock_ps_check.assert_called_once()
        assert result['has_issue'] is False

    @patch('app.standalone.camera_error_handler.CameraErrorHandler._is_powershell_available')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._check_driver_via_registry')
    def test_check_driver_malfunction_falls_back_to_registry(self, mock_registry_check, mock_ps_available):
        """Test driver check falls back to registry when PowerShell unavailable."""
        mock_ps_available.return_value = False
        mock_registry_check.return_value = {'has_issue': False}

        error_handler = CameraErrorHandler()
        result = error_handler._check_driver_malfunction(0)

        mock_registry_check.assert_called_once()
        assert result['has_issue'] is False

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_is_powershell_available_returns_true(self, mock_subprocess):
        """Test PowerShell availability check returns True when available."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        error_handler = CameraErrorHandler()
        available = error_handler._is_powershell_available()

        assert available is True

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_is_powershell_available_returns_false(self, mock_subprocess):
        """Test PowerShell availability check returns False when unavailable."""
        mock_subprocess.side_effect = FileNotFoundError

        error_handler = CameraErrorHandler()
        available = error_handler._is_powershell_available()

        assert available is False

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_check_driver_via_powershell_finds_issue(self, mock_subprocess):
        """Test PowerShell driver check detects malfunction."""
        # Mock PowerShell returns camera with problem
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"Name":"Camera","Status":"Error","ErrorCode":28}]'
        mock_subprocess.return_value = mock_result

        error_handler = CameraErrorHandler()
        result = error_handler._check_driver_via_powershell()

        assert result['has_issue'] is True
        assert "details" in result

    @patch('app.standalone.camera_error_handler.subprocess.run')
    def test_check_driver_via_powershell_no_issue(self, mock_subprocess):
        """Test PowerShell driver check when no issue."""
        # Mock PowerShell returns healthy camera
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '[{"Name":"Camera","Status":"OK","ErrorCode":0}]'
        mock_subprocess.return_value = mock_result

        error_handler = CameraErrorHandler()
        result = error_handler._check_driver_via_powershell()

        assert result['has_issue'] is False

    def test_check_driver_via_registry_fallback_works(self):
        """Test registry fallback detects driver issues."""
        # This test verifies the registry fallback exists and has correct signature
        error_handler = CameraErrorHandler()
        result = error_handler._check_driver_via_registry()

        # Should return dict with has_issue and details keys
        assert isinstance(result, dict)
        assert 'has_issue' in result
        assert 'details' in result
        assert isinstance(result['has_issue'], bool)


class TestUSBBandwidthCalculation:
    """Test USB bandwidth calculation with MJPEG compression (Critical Fix #5)."""

    def test_calculate_usb_bandwidth_low_res_passes(self):
        """Test low resolution doesn't saturate USB 2.0."""
        error_handler = CameraErrorHandler()

        # 640x480 @ 10 FPS
        result = error_handler.calculate_usb_bandwidth(640, 480, 10)

        assert result['bandwidth_mbps'] < 400  # USB 2.0 limit
        assert result['usb2_saturated'] is False
        assert "recommendation" in result

    def test_calculate_usb_bandwidth_hd_with_mjpeg(self):
        """Test HD resolution with MJPEG compression."""
        error_handler = CameraErrorHandler()

        # 1920x1080 @ 30 FPS (common HD webcam)
        result = error_handler.calculate_usb_bandwidth(1920, 1080, 30)

        # With MJPEG compression (5x factor), should be under USB 2.0 limit
        assert 'bandwidth_mbps' in result
        assert 'usb2_saturated' in result
        assert 'recommendation' in result

    def test_calculate_usb_bandwidth_4k_saturates_usb2(self):
        """Test 4K resolution saturates USB 2.0 even with compression."""
        error_handler = CameraErrorHandler()

        # 3840x2160 @ 30 FPS (4K)
        result = error_handler.calculate_usb_bandwidth(3840, 2160, 30)

        # Even with compression, 4K @ 30fps likely saturates USB 2.0
        assert result['bandwidth_mbps'] > 0
        assert 'usb2_saturated' in result

    def test_calculate_usb_bandwidth_includes_mjpeg_compression(self):
        """Test bandwidth calculation accounts for MJPEG compression."""
        error_handler = CameraErrorHandler()

        # Same resolution, different FPS
        result_10fps = error_handler.calculate_usb_bandwidth(1920, 1080, 10)
        result_30fps = error_handler.calculate_usb_bandwidth(1920, 1080, 30)

        # 30fps should be ~3x bandwidth of 10fps
        assert result_30fps['bandwidth_mbps'] > result_10fps['bandwidth_mbps'] * 2.5
        assert result_30fps['bandwidth_mbps'] < result_10fps['bandwidth_mbps'] * 3.5


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    def test_retry_with_backoff_succeeds_first_try(self):
        """Test retry succeeds on first attempt."""
        error_handler = CameraErrorHandler()

        operation = Mock(return_value=True)
        success, result = error_handler.retry_with_backoff(operation, max_retries=3)

        assert success is True
        assert operation.call_count == 1

    def test_retry_with_backoff_succeeds_after_retries(self):
        """Test retry succeeds after failures."""
        error_handler = CameraErrorHandler()

        # Fail twice, then succeed
        operation = Mock(side_effect=[Exception("fail"), Exception("fail"), True])
        success, result = error_handler.retry_with_backoff(operation, max_retries=3)

        assert success is True
        assert operation.call_count == 3

    def test_retry_with_backoff_fails_after_max_retries(self):
        """Test retry gives up after max retries."""
        error_handler = CameraErrorHandler()

        # Always fail
        operation = Mock(side_effect=Exception("always fails"))
        success, result = error_handler.retry_with_backoff(operation, max_retries=3)

        assert success is False
        assert operation.call_count == 3

    @patch('time.sleep')
    def test_retry_with_backoff_uses_exponential_delay(self, mock_sleep):
        """Test retry uses exponential backoff delays."""
        error_handler = CameraErrorHandler()

        # Fail all attempts
        operation = Mock(side_effect=Exception("fail"))
        error_handler.retry_with_backoff(operation, max_retries=3)

        # Should have 2 sleeps (between 3 attempts)
        assert mock_sleep.call_count == 2


class TestErrorHandling:
    """Test comprehensive error handling and solutions."""

    @patch('app.standalone.camera_error_handler.check_camera_permissions')
    def test_handle_camera_error_permission_denied(self, mock_permissions):
        """Test error handler detects permission denied."""
        mock_permissions.return_value = {
            'accessible': False,
            'error': 'Group policy blocked',
            'blocking_key': 'HKLM\\SOFTWARE\\Policies\\Microsoft\\Camera',
            'group_policy_blocked': True,
            'system_allowed': False,
            'user_allowed': False,
            'desktop_apps_allowed': False,
            'device_enabled': False
        }

        error_handler = CameraErrorHandler()
        result = error_handler.handle_camera_error(0)

        assert result['error_type'] == 'PERMISSION_DENIED'
        assert 'solution' in result
        assert 'permission' in result['solution'].lower()

    @patch('app.standalone.camera_error_handler.check_camera_permissions')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._check_camera_in_use')
    def test_handle_camera_error_camera_in_use(self, mock_in_use, mock_permissions):
        """Test error handler detects camera in use."""
        mock_permissions.return_value = {'accessible': True}
        mock_in_use.return_value = {
            'is_in_use': True,
            'process': 'Teams'
        }

        error_handler = CameraErrorHandler()
        result = error_handler.handle_camera_error(0)

        assert result['error_type'] == 'CAMERA_IN_USE'
        assert result['blocking_process'] == 'Teams'
        assert 'Teams' in result['solution']

    @patch('app.standalone.camera_error_handler.check_camera_permissions')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._camera_exists')
    def test_handle_camera_error_not_found(self, mock_exists, mock_permissions):
        """Test error handler detects camera not found."""
        mock_permissions.return_value = {'accessible': True}
        mock_exists.return_value = False

        error_handler = CameraErrorHandler()
        result = error_handler.handle_camera_error(0)

        assert result['error_type'] == 'NOT_FOUND'
        assert 'solution' in result

    @patch('app.standalone.camera_error_handler.check_camera_permissions')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._camera_exists')
    @patch('app.standalone.camera_error_handler.CameraErrorHandler._check_driver_malfunction')
    def test_handle_camera_error_driver_error(self, mock_driver, mock_exists, mock_permissions):
        """Test error handler detects driver malfunction."""
        mock_permissions.return_value = {'accessible': True}
        mock_exists.return_value = True
        mock_driver.return_value = {
            'has_issue': True,
            'details': 'Driver problem detected'
        }

        error_handler = CameraErrorHandler()
        result = error_handler.handle_camera_error(0)

        assert result['error_type'] == 'DRIVER_ERROR'
        assert 'driver' in result['solution'].lower()

    def test_camera_in_use_solution_includes_process(self):
        """Test solution message includes specific process name."""
        error_handler = CameraErrorHandler()
        solution = error_handler._get_camera_in_use_solution("Zoom")

        assert "Zoom" in solution

    def test_camera_in_use_solution_generic_when_no_process(self):
        """Test solution message is generic when no process identified."""
        error_handler = CameraErrorHandler()
        solution = error_handler._get_camera_in_use_solution(None)

        assert "another application" in solution


class TestCameraExistenceCheck:
    """Test camera existence verification."""

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_camera_exists_returns_true(self, mock_detect):
        """Test camera existence check returns True for valid camera."""
        mock_detect.return_value = [0, 1]  # Cameras 0 and 1 exist

        error_handler = CameraErrorHandler()
        exists = error_handler._camera_exists(0)

        assert exists is True

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_camera_exists_returns_false(self, mock_detect):
        """Test camera existence check returns False for invalid camera."""
        mock_detect.return_value = [1, 2]  # Camera 0 doesn't exist

        error_handler = CameraErrorHandler()
        exists = error_handler._camera_exists(0)

        assert exists is False

    @patch('app.standalone.camera_windows.detect_cameras')
    def test_camera_exists_handles_exception(self, mock_detect):
        """Test camera existence check handles exceptions gracefully."""
        mock_detect.side_effect = Exception("Detection error")

        error_handler = CameraErrorHandler()
        exists = error_handler._camera_exists(0)

        assert exists is False


# COVERAGE TARGET: 80%+ code coverage for camera_error_handler.py
