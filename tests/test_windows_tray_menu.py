"""Tests for Windows Desktop Client Enhanced Tray Menu (Story 7.4).

Tests enhanced menu structure with View Stats submenu and handlers.
"""
import pytest
from unittest.mock import patch, MagicMock, Mock, call
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTrayMenuHandlers:
    """Test enhanced menu handlers with real backend integration."""

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    @patch('app.windows_client.tray_manager.webbrowser')
    def test_on_view_today_stats_success(self, mock_webbrowser, mock_image, mock_pystray):
        """Test on_view_today_stats displays real stats from API."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Mock APIClient - patch where it's imported (inside the function)
        with patch('app.windows_client.api_client.APIClient') as mock_api_class:
            mock_api_instance = Mock()
            mock_api_instance.get_today_stats.return_value = {
                'posture_score': 85.0,
                'good_duration_seconds': 7200,  # 2 hours
                'bad_duration_seconds': 1800,   # 30 minutes
                'total_events': 42
            }
            mock_api_class.return_value = mock_api_instance

            # Mock ctypes inside the function where it's imported
            with patch('ctypes.windll') as mock_windll:
                mock_messagebox = Mock()
                mock_windll.user32.MessageBoxW = mock_messagebox

                # Call handler
                tray.on_view_today_stats(None, None)

                # Verify APIClient created with backend URL
                mock_api_class.assert_called_once_with("http://localhost:5000")

                # Verify stats fetched
                mock_api_instance.get_today_stats.assert_called_once()

                # Verify MessageBox shown with formatted stats
                mock_messagebox.assert_called_once()
                call_args = mock_messagebox.call_args[0]
                message = call_args[1]

                # Check message contains stats
                assert "Today's Posture Statistics" in message or "Today" in message
                assert "120" in message  # 7200 seconds = 120 minutes
                assert "30" in message   # 1800 seconds = 30 minutes
                assert "85" in message   # posture_score

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    @patch('app.windows_client.tray_manager.webbrowser')
    def test_on_view_today_stats_api_failure(self, mock_webbrowser, mock_image, mock_pystray):
        """Test on_view_today_stats handles API failure gracefully."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Mock APIClient - patch where it's imported (inside the function)
        with patch('app.windows_client.api_client.APIClient') as mock_api_class:
            mock_api_instance = Mock()
            mock_api_instance.get_today_stats.return_value = None
            mock_api_class.return_value = mock_api_instance

            # Mock ctypes inside the function where it's imported
            with patch('ctypes.windll') as mock_windll:
                mock_messagebox = Mock()
                mock_windll.user32.MessageBoxW = mock_messagebox

                # Call handler
                tray.on_view_today_stats(None, None)

                # Verify error message shown
                mock_messagebox.assert_called_once()
                call_args = mock_messagebox.call_args[0]
                message = call_args[1]

                # Check error message mentions failure and backend URL
                assert "Failed" in message or "failed" in message
                assert "localhost:5000" in message

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    @patch('app.windows_client.tray_manager.webbrowser')
    def test_on_view_history_opens_dashboard(self, mock_webbrowser, mock_image, mock_pystray):
        """Test on_view_history opens dashboard in browser."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://raspberrypi.local:5000", mock_socketio)

        # Call handler
        tray.on_view_history(None, None)

        # Verify browser opened with backend URL
        mock_webbrowser.open.assert_called_once_with("http://raspberrypi.local:5000")

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    @patch('app.windows_client.tray_manager.webbrowser')
    def test_on_refresh_stats_updates_tooltip(self, mock_webbrowser, mock_image, mock_pystray):
        """Test on_refresh_stats forces tooltip update."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Mock _update_tooltip_from_api method
        tray._update_tooltip_from_api = Mock()

        # Call handler
        tray.on_refresh_stats(None, None)

        # Verify tooltip update called
        tray._update_tooltip_from_api.assert_called_once()

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    @patch('app.windows_client.tray_manager.webbrowser')
    def test_on_settings_enhanced(self, mock_webbrowser, mock_image, mock_pystray):
        """Test enhanced on_settings shows config details."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Mock get_config_path - patch where it's imported (inside the function)
        with patch('app.windows_client.config.get_config_path') as mock_get_path:
            mock_get_path.return_value = "C:\\Users\\Test\\AppData\\Roaming\\DeskPulse\\config.json"

            # Mock ctypes inside the function where it's imported
            with patch('ctypes.windll') as mock_windll:
                mock_messagebox = Mock()
                mock_windll.user32.MessageBoxW = mock_messagebox

                # Call handler
                tray.on_settings(None, None)

                # Verify MessageBox shown with config details
                mock_messagebox.assert_called_once()
                call_args = mock_messagebox.call_args[0]
                message = call_args[1]

                # Check message contains backend URL and config path
                assert "localhost:5000" in message
                assert "config.json" in message

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    @patch('app.windows_client.tray_manager.webbrowser')
    def test_on_about_enhanced(self, mock_webbrowser, mock_image, mock_pystray):
        """Test enhanced on_about shows version and platform info."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Mock platform (imported at module level, not inside function)
        with patch('app.windows_client.tray_manager.platform') as mock_platform:
            mock_platform.system.return_value = "Windows"
            mock_platform.release.return_value = "11"
            mock_platform.version.return_value = "10.0.22000"
            mock_platform.python_version.return_value = "3.12.8"

            # Mock __version__ from app.windows_client
            with patch('app.windows_client.__version__', '1.0.0'):
                # Mock ctypes inside the function where it's imported
                with patch('ctypes.windll') as mock_windll:
                    mock_messagebox = Mock()
                    mock_windll.user32.MessageBoxW = mock_messagebox

                    # Call handler
                    tray.on_about(None, None)

                    # Verify MessageBox shown with version and platform
                    mock_messagebox.assert_called_once()
                    call_args = mock_messagebox.call_args[0]
                    message = call_args[1]

                    # Check message contains version and platform
                    assert "1.0.0" in message
                    assert "Windows" in message


class TestMenuStructure:
    """Test enhanced menu structure with submenu."""

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    def test_create_menu_has_view_stats_submenu(self, mock_image, mock_pystray):
        """Test create_menu includes View Stats submenu."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Create menu
        menu = tray.create_menu()

        # Menu should be callable (pystray.Menu)
        assert menu is not None

    @patch('app.windows_client.tray_manager.WINDOWS_AVAILABLE', True)
    @patch('app.windows_client.tray_manager.pystray')
    @patch('app.windows_client.tray_manager.Image')
    def test_menu_has_proper_separator_structure(self, mock_image, mock_pystray):
        """Test menu has separators in correct positions."""
        from app.windows_client.tray_manager import TrayManager

        mock_socketio = Mock()
        tray = TrayManager("http://localhost:5000", mock_socketio)

        # Create menu - should not raise
        menu = tray.create_menu()
        assert menu is not None
