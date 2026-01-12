"""
Unit tests for camera permissions module (Task 4).

Tests:
- All 5 registry key checks
- Group Policy detection
- Error message generation
- Permission detection logic
- Default Allow when keys missing
- Non-admin user handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.standalone.camera_permissions import (
    check_camera_permissions,
    get_permission_error_message,
    _check_group_policy_camera_access,
    _check_system_camera_access,
    _check_user_camera_access,
    _check_desktop_apps_camera_access
)


class TestCameraPermissions:
    """Test comprehensive camera permission checking."""

    @patch('app.standalone.camera_permissions._check_group_policy_camera_access')
    @patch('app.standalone.camera_permissions._check_system_camera_access')
    @patch('app.standalone.camera_permissions._check_user_camera_access')
    @patch('app.standalone.camera_permissions._check_desktop_apps_camera_access')
    def test_all_permissions_allowed(self, mock_desktop, mock_user, mock_system, mock_gp):
        """Test all permissions allowed returns accessible=True."""
        # All checks pass
        mock_gp.return_value = False  # Not blocked
        mock_system.return_value = True
        mock_user.return_value = True
        mock_desktop.return_value = True

        result = check_camera_permissions()

        assert result['accessible'] is True
        assert result['error'] is None
        assert result['group_policy_blocked'] is False
        assert result['system_allowed'] is True
        assert result['user_allowed'] is True
        assert result['desktop_apps_allowed'] is True

    @patch('app.standalone.camera_permissions._check_group_policy_camera_access')
    def test_group_policy_blocks_camera(self, mock_gp):
        """Test Group Policy block is detected."""
        # Group Policy blocks
        mock_gp.return_value = True

        result = check_camera_permissions()

        assert result['accessible'] is False
        assert result['group_policy_blocked'] is True
        assert result['error'] == 'Camera blocked by Enterprise Group Policy'
        assert 'LetAppsAccessCamera' in result['blocking_key']

    @patch('app.standalone.camera_permissions._check_group_policy_camera_access')
    @patch('app.standalone.camera_permissions._check_system_camera_access')
    def test_system_wide_disabled(self, mock_system, mock_gp):
        """Test system-wide camera access disabled."""
        mock_gp.return_value = False
        mock_system.return_value = False

        result = check_camera_permissions()

        assert result['accessible'] is False
        assert result['system_allowed'] is False
        assert result['error'] == 'System-wide camera access disabled'
        assert 'CapabilityAccessManager' in result['blocking_key']

    @patch('app.standalone.camera_permissions._check_group_policy_camera_access')
    @patch('app.standalone.camera_permissions._check_system_camera_access')
    @patch('app.standalone.camera_permissions._check_user_camera_access')
    def test_user_level_disabled(self, mock_user, mock_system, mock_gp):
        """Test user-level camera access disabled."""
        mock_gp.return_value = False
        mock_system.return_value = True
        mock_user.return_value = False

        result = check_camera_permissions()

        assert result['accessible'] is False
        assert result['user_allowed'] is False
        assert result['error'] == 'User-level camera access disabled'

    @patch('app.standalone.camera_permissions._check_group_policy_camera_access')
    @patch('app.standalone.camera_permissions._check_system_camera_access')
    @patch('app.standalone.camera_permissions._check_user_camera_access')
    @patch('app.standalone.camera_permissions._check_desktop_apps_camera_access')
    def test_desktop_apps_disabled(self, mock_desktop, mock_user, mock_system, mock_gp):
        """Test desktop apps camera access disabled (NonPackaged key)."""
        mock_gp.return_value = False
        mock_system.return_value = True
        mock_user.return_value = True
        mock_desktop.return_value = False

        result = check_camera_permissions()

        assert result['accessible'] is False
        assert result['desktop_apps_allowed'] is False
        assert result['error'] == 'Desktop app camera access disabled'
        assert 'NonPackaged' in result['blocking_key']


class TestGroupPolicyChecking:
    """Test Group Policy checking logic."""

    @patch('app.standalone.camera_permissions.winreg')
    def test_group_policy_force_deny(self, mock_winreg):
        """Test Group Policy with Force Deny (value=1) blocks camera."""
        # Mock registry returns value=1 (Force Deny)
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = (1, None)

        result = _check_group_policy_camera_access()

        assert result is True  # Blocked

    @patch('app.standalone.camera_permissions.winreg')
    def test_group_policy_force_allow(self, mock_winreg):
        """Test Group Policy with Force Allow (value=2) allows camera."""
        # Mock registry returns value=2 (Force Allow)
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = (2, None)

        result = _check_group_policy_camera_access()

        assert result is False  # Allowed

    @patch('app.standalone.camera_permissions.winreg')
    def test_group_policy_key_missing_allows(self, mock_winreg):
        """Test missing Group Policy key defaults to Allow."""
        # Mock registry key not found
        mock_winreg.OpenKey.side_effect = FileNotFoundError()

        result = _check_group_policy_camera_access()

        assert result is False  # Allowed (no policy)

    @patch('app.standalone.camera_permissions.winreg')
    def test_group_policy_permission_error_allows(self, mock_winreg):
        """Test Group Policy check with permission error defaults to Allow."""
        # Mock permission denied
        mock_winreg.OpenKey.side_effect = OSError("Access denied")

        result = _check_group_policy_camera_access()

        assert result is False  # Allowed (safe default for non-admin)


class TestSystemCameraAccess:
    """Test system-wide camera access checking."""

    @patch('app.standalone.camera_permissions.winreg')
    def test_system_camera_access_allowed(self, mock_winreg):
        """Test system camera access with Allow value."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("Allow", None)

        result = _check_system_camera_access()

        assert result is True

    @patch('app.standalone.camera_permissions.winreg')
    def test_system_camera_access_denied(self, mock_winreg):
        """Test system camera access with Deny value."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("Deny", None)

        result = _check_system_camera_access()

        assert result is False

    @patch('app.standalone.camera_permissions.winreg')
    def test_system_camera_key_missing_allows(self, mock_winreg):
        """Test missing system camera key defaults to Allow."""
        mock_winreg.OpenKey.side_effect = FileNotFoundError()

        result = _check_system_camera_access()

        assert result is True  # Default allow


class TestUserCameraAccess:
    """Test user-level camera access checking."""

    @patch('app.standalone.camera_permissions.winreg')
    def test_user_camera_access_allowed(self, mock_winreg):
        """Test user camera access with Allow value."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("Allow", None)

        result = _check_user_camera_access()

        assert result is True

    @patch('app.standalone.camera_permissions.winreg')
    def test_user_camera_access_denied(self, mock_winreg):
        """Test user camera access with Deny value."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("Deny", None)

        result = _check_user_camera_access()

        assert result is False

    @patch('app.standalone.camera_permissions.winreg')
    def test_user_camera_key_missing_allows(self, mock_winreg):
        """Test missing user camera key defaults to Allow."""
        mock_winreg.OpenKey.side_effect = FileNotFoundError()

        result = _check_user_camera_access()

        assert result is True  # Default allow


class TestDesktopAppsCameraAccess:
    """Test desktop apps camera access checking (NonPackaged key)."""

    @patch('app.standalone.camera_permissions.winreg')
    def test_desktop_apps_access_allowed(self, mock_winreg):
        """Test desktop apps camera access with Allow value."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("Allow", None)

        result = _check_desktop_apps_camera_access()

        assert result is True

    @patch('app.standalone.camera_permissions.winreg')
    def test_desktop_apps_access_denied(self, mock_winreg):
        """Test desktop apps camera access with Deny value."""
        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
        mock_winreg.QueryValueEx.return_value = ("Deny", None)

        result = _check_desktop_apps_camera_access()

        assert result is False

    @patch('app.standalone.camera_permissions.winreg')
    def test_desktop_apps_key_missing_allows(self, mock_winreg):
        """Test missing desktop apps key defaults to Allow."""
        mock_winreg.OpenKey.side_effect = FileNotFoundError()

        result = _check_desktop_apps_camera_access()

        assert result is True  # Default allow


class TestErrorMessageGeneration:
    """Test error message generation."""

    def test_error_message_for_group_policy_block(self):
        """Test error message for Group Policy block."""
        permissions = {
            'accessible': False,
            'group_policy_blocked': True,
            'error': 'Camera blocked by Enterprise Group Policy',
            'blocking_key': 'HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\AppPrivacy\\LetAppsAccessCamera'
        }

        message = get_permission_error_message(permissions)

        assert 'Enterprise Group Policy' in message
        assert 'IT administrator' in message
        assert 'LetAppsAccessCamera' in message

    def test_error_message_for_system_disabled(self):
        """Test error message for system-wide disabled."""
        permissions = {
            'accessible': False,
            'group_policy_blocked': False,
            'system_allowed': False,
            'error': 'System-wide camera access disabled',
            'blocking_key': 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam'
        }

        message = get_permission_error_message(permissions)

        assert 'system-wide' in message
        assert 'Privacy & security > Camera' in message
        assert '0xA00F4244' in message

    def test_error_message_for_user_disabled(self):
        """Test error message for user-level disabled."""
        permissions = {
            'accessible': False,
            'group_policy_blocked': False,
            'system_allowed': True,
            'user_allowed': False,
            'error': 'User-level camera access disabled',
            'blocking_key': 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam'
        }

        message = get_permission_error_message(permissions)

        assert 'user-level' in message
        assert 'Let apps access your camera' in message
        assert '0xA00F4244' in message

    def test_error_message_for_desktop_apps_disabled(self):
        """Test error message for desktop apps disabled."""
        permissions = {
            'accessible': False,
            'group_policy_blocked': False,
            'system_allowed': True,
            'user_allowed': True,
            'desktop_apps_allowed': False,
            'error': 'Desktop app camera access disabled',
            'blocking_key': 'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\webcam\\NonPackaged'
        }

        message = get_permission_error_message(permissions)

        assert 'Desktop app permission' in message
        assert 'Let desktop apps access your camera' in message
        assert 'NonPackaged' in message

    def test_no_error_message_when_accessible(self):
        """Test no error message when camera is accessible."""
        permissions = {
            'accessible': True,
            'error': None
        }

        message = get_permission_error_message(permissions)

        assert message == ""
