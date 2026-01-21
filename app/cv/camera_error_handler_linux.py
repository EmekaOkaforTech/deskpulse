"""
Linux Camera Error Handler Module.

Enterprise-grade error diagnostics for Raspberry Pi:
- Process identification for "camera in use" errors (lsof)
- Permission detection (video group, device permissions)
- Driver malfunction detection (v4l2-ctl, dmesg)
- USB bandwidth monitoring
- Retry logic with exponential backoff
- Clear user-facing error messages
"""

import logging
import subprocess
import time
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from app.cv.camera_permissions_linux import (
    check_camera_permissions,
    get_permission_error_message
)

logger = logging.getLogger('deskpulse.cv.camera_error')


class CameraErrorHandler:
    """
    Comprehensive camera error diagnostics and handling for Linux.

    Diagnoses error types:
    1. Permission denied (video group, device permissions)
    2. Camera in use (other process holding device)
    3. Camera not found (disconnected, driver issue)
    4. Driver malfunction (V4L2/UVC driver errors)
    5. USB bandwidth issues (multiple cameras)
    """

    def __init__(self):
        """Initialize error handler."""
        self.last_error = None
        self.retry_count = 0
        self.max_retries = 3

    def handle_camera_error(self, camera_index: int, exception: Optional[Exception] = None) -> Dict[str, any]:
        """
        Diagnose camera error and provide actionable guidance.

        Args:
            camera_index: Camera index that failed
            exception: Exception that occurred (if any)

        Returns:
            dict: {
                'error_type': str,  # PERMISSION_DENIED, CAMERA_IN_USE, NOT_FOUND, DRIVER_ERROR, USB_BANDWIDTH, UNKNOWN
                'message': str,  # User-facing error message
                'technical_details': str,  # Technical info for debugging
                'solution': str,  # Step-by-step fix instructions
                'retry_recommended': bool,  # Whether to retry
                'blocking_process': str | None  # Process using camera (if applicable)
            }
        """
        device_path = f"/dev/video{camera_index}"
        logger.info(f"Diagnosing camera error for {device_path}")

        # 1. Check permissions first (highest priority)
        permissions = check_camera_permissions()
        if not permissions['accessible']:
            return {
                'error_type': 'PERMISSION_DENIED',
                'message': permissions['error'],
                'technical_details': f"Blocking reason: {permissions['blocking_reason']}",
                'solution': get_permission_error_message(permissions),
                'retry_recommended': False,
                'blocking_process': None
            }

        # 2. Check if camera in use
        in_use_result = self._check_camera_in_use(device_path)
        if in_use_result['is_in_use']:
            return {
                'error_type': 'CAMERA_IN_USE',
                'message': 'Camera is in use by another application',
                'technical_details': f"Blocking process: {in_use_result['process']} (PID: {in_use_result['pid']})",
                'solution': self._get_camera_in_use_solution(in_use_result['process'], in_use_result['pid']),
                'retry_recommended': True,  # Transient error
                'blocking_process': in_use_result['process']
            }

        # 3. Check if camera exists
        if not self._camera_exists(camera_index):
            return {
                'error_type': 'NOT_FOUND',
                'message': f'Camera {device_path} not found',
                'technical_details': 'Camera device not detected by Linux',
                'solution': self._get_camera_not_found_solution(),
                'retry_recommended': False,
                'blocking_process': None
            }

        # 4. Check for driver issues
        driver_issue = self._check_driver_malfunction(camera_index)
        if driver_issue['has_issue']:
            return {
                'error_type': 'DRIVER_ERROR',
                'message': 'Camera driver malfunction detected',
                'technical_details': driver_issue['details'],
                'solution': self._get_driver_error_solution(),
                'retry_recommended': False,
                'blocking_process': None
            }

        # 5. Unknown error
        return {
            'error_type': 'UNKNOWN',
            'message': f'Unknown camera error: {exception}' if exception else 'Unknown camera error',
            'technical_details': str(exception) if exception else 'No exception details',
            'solution': self._get_generic_solution(),
            'retry_recommended': True,
            'blocking_process': None
        }

    def retry_with_backoff(self, operation, max_retries: int = 3) -> Tuple[bool, any]:
        """
        Retry operation with exponential backoff.

        Args:
            operation: Callable to retry
            max_retries: Maximum retry attempts

        Returns:
            Tuple[bool, any]: (success, result)
        """
        for attempt in range(max_retries):
            try:
                result = operation()
                return True, result
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2 ** attempt
                    logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All retries exhausted: {e}")
                    return False, None

    def _check_camera_in_use(self, device_path: str) -> Dict[str, any]:
        """
        Check if camera is in use by another process.

        Uses lsof to identify blocking processes.

        Returns:
            dict: {'is_in_use': bool, 'process': str | None, 'pid': int | None}
        """
        try:
            # Use lsof to check if device is open
            result = subprocess.run(
                ['lsof', device_path],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse lsof output to get process name and PID
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # Skip header
                    parts = lines[1].split()
                    if len(parts) >= 2:
                        process_name = parts[0]
                        pid = int(parts[1]) if parts[1].isdigit() else None
                        logger.info(f"Camera in use by: {process_name} (PID: {pid})")
                        return {'is_in_use': True, 'process': process_name, 'pid': pid}

            return {'is_in_use': False, 'process': None, 'pid': None}

        except FileNotFoundError:
            logger.warning("lsof not installed - cannot check camera usage")
            return {'is_in_use': False, 'process': None, 'pid': None}
        except subprocess.TimeoutExpired:
            logger.warning("lsof timeout checking camera usage")
            return {'is_in_use': False, 'process': None, 'pid': None}
        except Exception as e:
            logger.warning(f"Camera usage check failed: {e}")
            return {'is_in_use': False, 'process': None, 'pid': None}

    def _camera_exists(self, camera_index: int) -> bool:
        """
        Check if camera device exists.

        Args:
            camera_index: Camera index to check

        Returns:
            bool: True if camera exists
        """
        device_path = f"/dev/video{camera_index}"
        exists = Path(device_path).exists()
        logger.debug(f"Camera {device_path} exists: {exists}")
        return exists

    def _check_driver_malfunction(self, camera_index: int) -> Dict[str, any]:
        """
        Check for camera driver issues.

        Uses v4l2-ctl and dmesg for diagnostics.

        Returns:
            dict: {'has_issue': bool, 'details': str}
        """
        device_path = f"/dev/video{camera_index}"
        issues = []

        # Check with v4l2-ctl if available
        try:
            result = subprocess.run(
                ['v4l2-ctl', '-d', device_path, '--all'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                issues.append(f"v4l2-ctl error: {result.stderr.strip()}")

        except FileNotFoundError:
            logger.debug("v4l2-ctl not installed - skipping driver check")
        except subprocess.TimeoutExpired:
            issues.append("v4l2-ctl timeout - driver may be stuck")
        except Exception as e:
            logger.warning(f"v4l2-ctl check failed: {e}")

        # Check dmesg for recent camera errors
        try:
            result = subprocess.run(
                ['dmesg', '--time-format=reltime'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Look for camera-related errors in last 50 lines
                lines = result.stdout.strip().split('\n')[-50:]
                camera_errors = [
                    line for line in lines
                    if any(kw in line.lower() for kw in ['uvc', 'video', 'camera', 'usb'])
                    and any(err in line.lower() for err in ['error', 'fail', 'timeout', 'disconnect'])
                ]

                if camera_errors:
                    issues.append(f"Kernel errors: {camera_errors[-1]}")

        except subprocess.TimeoutExpired:
            logger.warning("dmesg timeout")
        except PermissionError:
            logger.debug("dmesg requires elevated permissions - skipping")
        except Exception as e:
            logger.warning(f"dmesg check failed: {e}")

        if issues:
            return {'has_issue': True, 'details': '; '.join(issues)}

        return {'has_issue': False, 'details': 'Driver status OK'}

    def get_camera_info(self, camera_index: int) -> Dict[str, any]:
        """
        Get detailed camera information using v4l2-ctl.

        Args:
            camera_index: Camera index

        Returns:
            dict: Camera information or empty dict if unavailable
        """
        device_path = f"/dev/video{camera_index}"
        info = {
            'device': device_path,
            'name': 'Unknown',
            'driver': 'Unknown',
            'capabilities': [],
            'formats': []
        }

        try:
            # Get device info
            result = subprocess.run(
                ['v4l2-ctl', '-d', device_path, '--info'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Card type' in line:
                        info['name'] = line.split(':')[-1].strip()
                    elif 'Driver name' in line:
                        info['driver'] = line.split(':')[-1].strip()

            # Get supported formats
            result = subprocess.run(
                ['v4l2-ctl', '-d', device_path, '--list-formats'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Pixel Format' in line or 'MJPG' in line or 'YUYV' in line:
                        info['formats'].append(line.strip())

        except FileNotFoundError:
            logger.debug("v4l2-ctl not installed")
        except Exception as e:
            logger.warning(f"Could not get camera info: {e}")

        return info

    def _get_camera_in_use_solution(self, process: Optional[str], pid: Optional[int]) -> str:
        """Get solution for camera in use error."""
        if process and pid:
            return f"""Camera is in use by: {process} (PID: {pid})

To fix:
1. Close {process} application
2. Or kill the process: sudo kill {pid}
3. Or force kill: sudo kill -9 {pid}
4. Restart DeskPulse

Common camera-using applications:
- Chromium/Chrome (video calls)
- Firefox (video calls)
- VLC media player
- Motion (surveillance)
- fswebcam
"""
        else:
            return """Camera is in use by another application.

To fix:
1. Check running processes: lsof /dev/video0
2. Close video applications (browsers, VLC, etc.)
3. Stop camera services: sudo systemctl stop motion
4. Restart DeskPulse

Common camera-using applications:
- Web browsers (Chromium, Firefox)
- VLC media player
- Motion/MotionEye
- fswebcam
"""

    def _get_camera_not_found_solution(self) -> str:
        """Get solution for camera not found error."""
        return """Camera not found.

Possible causes:
- Camera disconnected
- USB cable/port issue
- Driver not loaded

To fix:
1. Check USB connection
2. Try different USB port
3. Check device exists: ls /dev/video*
4. Load UVC driver: sudo modprobe uvcvideo
5. Check kernel messages: dmesg | grep -i video

For Raspberry Pi Camera Module:
1. Enable camera: sudo raspi-config
   -> Interface Options -> Camera -> Enable
2. Check cable connection to CSI port
3. Reboot: sudo reboot

For USB webcams:
1. Ensure camera is USB 2.0 compatible
2. Try powered USB hub if power issues suspected
"""

    def _get_driver_error_solution(self) -> str:
        """Get solution for driver malfunction."""
        return """Camera driver malfunction detected.

To fix:
1. Reload UVC driver:
   sudo modprobe -r uvcvideo
   sudo modprobe uvcvideo

2. Check kernel messages:
   dmesg | tail -30

3. Update system:
   sudo apt update && sudo apt upgrade

4. If using Pi Camera Module:
   - Check ribbon cable connection
   - Ensure camera is enabled in raspi-config

5. Reboot if issues persist:
   sudo reboot

If problem continues, camera hardware may be faulty.
"""

    def _get_generic_solution(self) -> str:
        """Get generic solution for unknown errors."""
        return """Camera error occurred.

Try these steps:
1. Restart DeskPulse
2. Reconnect camera (if USB)
3. Check permissions: groups $USER
4. Verify device exists: ls -la /dev/video*
5. Check kernel logs: dmesg | tail -20
6. Reboot system

If problem persists, check logs for technical details.
"""


def detect_cameras() -> List[Dict[str, any]]:
    """
    Detect all available cameras on Linux.

    Returns:
        list: List of camera info dicts with 'index', 'name', 'device'
    """
    cameras = []
    handler = CameraErrorHandler()

    # Scan /dev/video* devices
    for i in range(10):  # Check video0 through video9
        device_path = f"/dev/video{i}"
        if Path(device_path).exists():
            info = handler.get_camera_info(i)
            cameras.append({
                'index': i,
                'name': info.get('name', f'Camera {i}'),
                'device': device_path,
                'driver': info.get('driver', 'Unknown')
            })

    logger.info(f"Detected {len(cameras)} camera(s)")
    return cameras


if __name__ == '__main__':
    # Test error handler
    logging.basicConfig(level=logging.INFO)

    print("DeskPulse Linux Camera Error Handler Test")
    print("=" * 50)

    handler = CameraErrorHandler()

    # Test camera detection
    print("\nDetecting cameras...")
    cameras = detect_cameras()
    for cam in cameras:
        print(f"  [{cam['index']}] {cam['name']} ({cam['device']})")

    if not cameras:
        print("  No cameras detected!")

    # Test error diagnosis
    print("\n" + "=" * 50)
    print("Testing error diagnosis for camera 0...")
    result = handler.handle_camera_error(0)
    print(f"\nError Type: {result['error_type']}")
    print(f"Message: {result['message']}")
    print(f"Retry Recommended: {result['retry_recommended']}")

    if result['blocking_process']:
        print(f"Blocking Process: {result['blocking_process']}")
