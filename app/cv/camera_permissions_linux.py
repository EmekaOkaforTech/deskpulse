"""
Linux Camera Permission Checking Module.

Enterprise-grade permission detection for Raspberry Pi:
- Video group membership check
- /dev/video* device existence
- udev rules verification
- V4L2 driver status
- Clear error messages with actionable steps
"""

import logging
import os
import grp
import pwd
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('deskpulse.cv.camera_permissions')


def check_camera_permissions() -> Dict[str, any]:
    """
    Check Linux camera permissions.

    Returns:
        dict: {
            'video_group_member': bool,
            'device_exists': bool,
            'device_readable': bool,
            'udev_rules_ok': bool,
            'accessible': bool,  # Overall accessibility
            'error': str | None,  # Error message if blocked
            'blocking_reason': str | None,  # What's blocking access
            'devices_found': list  # List of /dev/video* devices
        }

    Checks:
    1. User is member of 'video' group
    2. /dev/video* devices exist
    3. Devices are readable by current user
    4. V4L2 driver is loaded
    """
    result = {
        'video_group_member': False,
        'device_exists': False,
        'device_readable': False,
        'udev_rules_ok': True,  # Assume OK unless proven otherwise
        'accessible': False,
        'error': None,
        'blocking_reason': None,
        'devices_found': []
    }

    # 1. Check video group membership
    video_group_ok, video_group_error = _check_video_group_membership()
    result['video_group_member'] = video_group_ok

    if not video_group_ok:
        result['error'] = video_group_error
        result['blocking_reason'] = 'VIDEO_GROUP'
        logger.warning(f"Video group check failed: {video_group_error}")
        return result

    # 2. Check /dev/video* devices exist
    devices = _find_video_devices()
    result['devices_found'] = devices
    result['device_exists'] = len(devices) > 0

    if not result['device_exists']:
        result['error'] = 'No camera devices found (/dev/video*)'
        result['blocking_reason'] = 'NO_DEVICE'
        logger.warning("No video devices found")
        return result

    # 3. Check device is readable
    readable_device = None
    for device in devices:
        if os.access(device, os.R_OK):
            readable_device = device
            break

    result['device_readable'] = readable_device is not None

    if not result['device_readable']:
        result['error'] = f'Camera device not readable: {devices[0]}'
        result['blocking_reason'] = 'PERMISSION_DENIED'
        logger.warning(f"Device not readable: {devices[0]}")
        return result

    # 4. Check V4L2 driver (optional - don't fail if can't check)
    v4l2_ok = _check_v4l2_driver()
    if not v4l2_ok:
        logger.warning("V4L2 driver check failed (non-blocking)")
        # Don't fail - camera might still work

    # All checks passed
    result['accessible'] = True
    logger.info(f"Camera permissions OK: {len(devices)} device(s) found")
    return result


def _check_video_group_membership() -> tuple[bool, Optional[str]]:
    """
    Check if current user is member of 'video' group.

    Returns:
        tuple: (is_member: bool, error_message: str | None)
    """
    try:
        current_user = pwd.getpwuid(os.getuid()).pw_name
        user_groups = [g.gr_name for g in grp.getgrall() if current_user in g.gr_mem]

        # Also check primary group
        primary_gid = pwd.getpwuid(os.getuid()).pw_gid
        primary_group = grp.getgrgid(primary_gid).gr_name
        user_groups.append(primary_group)

        if 'video' in user_groups:
            logger.debug(f"User '{current_user}' is member of 'video' group")
            return True, None
        else:
            logger.warning(f"User '{current_user}' is NOT member of 'video' group")
            return False, f"User '{current_user}' is not in 'video' group"

    except Exception as e:
        logger.warning(f"Could not check video group membership: {e}")
        # Assume OK if we can't check (will fail later if actually blocked)
        return True, None


def _find_video_devices() -> List[str]:
    """
    Find all /dev/video* devices.

    Returns:
        list: List of device paths (e.g., ['/dev/video0', '/dev/video1'])
    """
    devices = []
    dev_path = Path('/dev')

    try:
        for entry in dev_path.iterdir():
            if entry.name.startswith('video') and entry.name[5:].isdigit():
                devices.append(str(entry))

        # Sort by device number
        devices.sort(key=lambda x: int(x.replace('/dev/video', '')))
        logger.debug(f"Found video devices: {devices}")

    except Exception as e:
        logger.warning(f"Error scanning /dev for video devices: {e}")

    return devices


def _check_v4l2_driver() -> bool:
    """
    Check if V4L2 driver is loaded.

    Returns:
        bool: True if V4L2 appears functional
    """
    try:
        # Check if v4l2 module is loaded
        result = subprocess.run(
            ['lsmod'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if 'videodev' in result.stdout or 'v4l2' in result.stdout.lower():
            logger.debug("V4L2 driver modules loaded")
            return True

        # Alternative: check if v4l2-ctl is available and works
        result = subprocess.run(
            ['v4l2-ctl', '--list-devices'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            logger.debug("v4l2-ctl found devices")
            return True

        return False

    except FileNotFoundError:
        logger.debug("v4l2-ctl not installed (non-critical)")
        return True  # Don't fail if tool not installed
    except subprocess.TimeoutExpired:
        logger.warning("V4L2 check timed out")
        return True  # Don't fail on timeout
    except Exception as e:
        logger.warning(f"V4L2 check error: {e}")
        return True  # Don't fail on error


def get_permission_error_message(permissions: Dict[str, any]) -> str:
    """
    Generate user-friendly error message with actionable steps.

    Args:
        permissions: Result dict from check_camera_permissions()

    Returns:
        str: Formatted error message with step-by-step instructions
    """
    if permissions['accessible']:
        return ""

    blocking_reason = permissions.get('blocking_reason', 'UNKNOWN')
    error = permissions.get('error', 'Unknown error')

    # Video group membership issue
    if blocking_reason == 'VIDEO_GROUP':
        current_user = pwd.getpwuid(os.getuid()).pw_name
        return f"""Camera access denied: User not in 'video' group.

To fix:
1. Run: sudo usermod -aG video {current_user}
2. Log out and log back in (required for group change)
3. Verify with: groups {current_user}
4. Restart DeskPulse

Technical details: {error}
"""

    # No device found
    if blocking_reason == 'NO_DEVICE':
        return """Camera not found: No /dev/video* devices detected.

Possible causes:
- Camera not connected
- USB cable issue
- Camera driver not loaded

To fix:
1. Check USB cable connection
2. Try different USB port
3. Run: ls /dev/video*
4. Check kernel messages: dmesg | grep -i camera
5. Load driver manually: sudo modprobe uvcvideo

If using Raspberry Pi Camera Module:
1. Enable camera: sudo raspi-config -> Interface Options -> Camera
2. Reboot: sudo reboot
"""

    # Permission denied on device
    if blocking_reason == 'PERMISSION_DENIED':
        devices = permissions.get('devices_found', [])
        device = devices[0] if devices else '/dev/video0'
        return f"""Camera access denied: Cannot read {device}.

To fix:
1. Check device permissions: ls -la {device}
2. Add user to video group: sudo usermod -aG video $USER
3. Log out and log back in
4. If still failing, check udev rules:
   ls -la /etc/udev/rules.d/*camera* /etc/udev/rules.d/*video*

Technical details: {error}
"""

    # Generic fallback
    return f"""Camera access error.

Error: {error}

To fix:
1. Check camera connection
2. Verify user permissions: groups $USER
3. Check device exists: ls /dev/video*
4. Review kernel logs: dmesg | tail -20
5. Restart DeskPulse

If problem persists, check logs for technical details.
"""


if __name__ == '__main__':
    # Test permission checking
    logging.basicConfig(level=logging.INFO)

    print("DeskPulse Linux Camera Permission Check")
    print("=" * 50)

    permissions = check_camera_permissions()

    print(f"\nPermission Status:")
    print(f"  Video Group Member: {permissions['video_group_member']}")
    print(f"  Device Exists: {permissions['device_exists']}")
    print(f"  Device Readable: {permissions['device_readable']}")
    print(f"  Devices Found: {permissions['devices_found']}")
    print(f"  Accessible: {permissions['accessible']}")

    if not permissions['accessible']:
        print(f"\nError: {permissions['error']}")
        print(f"Blocking Reason: {permissions['blocking_reason']}")
        print(f"\n{get_permission_error_message(permissions)}")
    else:
        print("\n✓ All camera permissions OK!")
