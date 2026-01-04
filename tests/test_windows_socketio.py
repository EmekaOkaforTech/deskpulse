"""Tests for Windows Desktop Client SocketIO Wrapper."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.windows_client.socketio_client import SocketIOClient


class TestSocketIOClientInit:
    """Test SocketIO client initialization."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_init_creates_client(self, mock_client_class):
        """Test initialization creates SocketIO client with reconnection."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Verify SocketIO client created with reconnection settings
        mock_client_class.assert_called_once_with(
            reconnection=True,
            reconnection_delay=5,
            reconnection_delay_max=30,
            logger=False,
            engineio_logger=False
        )

        # Verify event handlers registered (Story 7.1: 4 handlers + Story 7.2: 2 handlers = 6 total)
        assert mock_sio.on.call_count == 6
        mock_sio.on.assert_any_call('connect', client.on_connect)
        mock_sio.on.assert_any_call('disconnect', client.on_disconnect)
        mock_sio.on.assert_any_call('monitoring_status', client.on_monitoring_status)
        mock_sio.on.assert_any_call('error', client.on_error)
        mock_sio.on.assert_any_call('alert_triggered', client.on_alert_triggered)
        mock_sio.on.assert_any_call('posture_corrected', client.on_posture_corrected)

        # Verify attributes stored
        assert client.backend_url == "http://localhost:5000"
        assert client.tray_manager == mock_tray


class TestSocketIOClientConnect:
    """Test SocketIO client connection."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_connect_success(self, mock_client_class):
        """Test successful connection."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        result = client.connect()

        assert result is True
        mock_sio.connect.assert_called_once_with("http://localhost:5000")

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_connect_failure(self, mock_client_class):
        """Test connection failure handling."""
        mock_sio = Mock()
        mock_sio.connect.side_effect = Exception("Connection refused")
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        result = client.connect()

        assert result is False


class TestSocketIOClientDisconnect:
    """Test SocketIO client disconnection."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_disconnect_when_connected(self, mock_client_class):
        """Test disconnect when client is connected."""
        mock_sio = Mock()
        mock_sio.connected = True
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.disconnect()

        mock_sio.disconnect.assert_called_once()

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_disconnect_when_not_connected(self, mock_client_class):
        """Test disconnect when client is not connected."""
        mock_sio = Mock()
        mock_sio.connected = False
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.disconnect()

        # Should not call disconnect if not connected
        mock_sio.disconnect.assert_not_called()


class TestSocketIOClientEvents:
    """Test SocketIO event handlers."""

    @patch('app.windows_client.socketio_client.requests.get')
    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_connect_updates_icon_and_fetches_stats(self, mock_client_class, mock_get):
        """Test on_connect updates icon and fetches stats."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_tray.update_tooltip = Mock()

        # Mock stats response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "posture_score": 85.0,
            "good_duration_seconds": 7200
        }
        mock_get.return_value = mock_response

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.on_connect()

        # Verify icon updated to connected
        mock_tray.update_icon_state.assert_called_once_with('connected')

        # Verify stats fetched
        mock_get.assert_called_once_with(
            "http://localhost:5000/api/stats/today",
            timeout=5
        )
        mock_tray.update_tooltip.assert_called_once()

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_disconnect_updates_icon(self, mock_client_class):
        """Test on_disconnect updates icon to disconnected."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_tray.update_tooltip = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.on_disconnect()

        # Verify icon updated to disconnected
        mock_tray.update_icon_state.assert_called_once_with('disconnected')
        mock_tray.update_tooltip.assert_called_once_with(None)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_monitoring_status_active(self, mock_client_class):
        """Test on_monitoring_status with monitoring active."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.on_monitoring_status({'monitoring_active': True})

        # Verify tray manager state updated
        assert mock_tray.monitoring_active is True

        # Verify icon updated to connected (green)
        mock_tray.update_icon_state.assert_called_once_with('connected')

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_monitoring_status_paused(self, mock_client_class):
        """Test on_monitoring_status with monitoring paused."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.on_monitoring_status({'monitoring_active': False})

        # Verify tray manager state updated
        assert mock_tray.monitoring_active is False

        # Verify icon updated to paused (gray)
        mock_tray.update_icon_state.assert_called_once_with('paused')


class TestSocketIOClientEmit:
    """Test emitting events to backend."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_emit_pause(self, mock_client_class):
        """Test emitting pause_monitoring event."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.emit_pause()

        # Verify pause_monitoring emitted
        mock_sio.emit.assert_called_once_with('pause_monitoring')

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_emit_resume(self, mock_client_class):
        """Test emitting resume_monitoring event."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.emit_resume()

        # Verify resume_monitoring emitted
        mock_sio.emit.assert_called_once_with('resume_monitoring')

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_emit_pause_error_handling(self, mock_client_class):
        """Test emit_pause handles errors gracefully."""
        mock_sio = Mock()
        mock_sio.emit.side_effect = Exception("Connection lost")
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        # Should not raise exception
        client.emit_pause()

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_emit_resume_error_handling(self, mock_client_class):
        """Test emit_resume handles errors gracefully."""
        mock_sio = Mock()
        mock_sio.emit.side_effect = Exception("Connection lost")
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        # Should not raise exception
        client.emit_resume()


class TestSocketIOClientProperties:
    """Test SocketIO client properties."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_is_connected_true(self, mock_client_class):
        """Test is_connected when connected."""
        mock_sio = Mock()
        mock_sio.connected = True
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        assert client.is_connected is True

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_is_connected_false(self, mock_client_class):
        """Test is_connected when disconnected."""
        mock_sio = Mock()
        mock_sio.connected = False
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        assert client.is_connected is False
