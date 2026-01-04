"""Comprehensive SocketIO Integration Tests - Story 7.3.

Tests Windows Desktop Client SocketIO integration with backend:
- Story 7.2 integration: alert_triggered, posture_corrected events
- WindowsNotifier integration (toast notifications)
- Tooltip update thread lifecycle
- Error handling and defensive extraction
- Enterprise-grade edge cases

This test suite complements test_windows_socketio.py (Story 7.1 core tests).
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.windows_client.socketio_client import SocketIOClient


class TestSocketIOStory72Integration:
    """Test Story 7.2 integration - alert_triggered and posture_corrected events."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_alert_triggered_with_notifier(self, mock_client_class):
        """Test on_alert_triggered calls WindowsNotifier with correct duration."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger alert with 600 seconds (10 minutes)
        event_data = {
            'duration': 600,
            'message': 'Bad posture detected for 10 minutes',
            'timestamp': '2025-01-04T10:30:00'
        }
        client.on_alert_triggered(event_data)

        # Verify notifier called with duration
        mock_notifier.show_posture_alert.assert_called_once_with(600)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_alert_triggered_without_notifier(self, mock_client_class):
        """Test on_alert_triggered handles missing notifier gracefully."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        # No notifier provided
        client = SocketIOClient("http://localhost:5000", mock_tray, notifier=None)

        # Should not raise exception
        event_data = {'duration': 600, 'message': 'Test', 'timestamp': '2025-01-04T10:30:00'}
        client.on_alert_triggered(event_data)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_alert_triggered_defensive_extraction(self, mock_client_class):
        """Test on_alert_triggered handles missing 'duration' field."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Missing 'duration' field (defensive extraction defaults to 0)
        event_data = {'message': 'Test', 'timestamp': '2025-01-04T10:30:00'}
        client.on_alert_triggered(event_data)

        # Should call with default value 0
        mock_notifier.show_posture_alert.assert_called_once_with(0)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_posture_corrected_with_notifier(self, mock_client_class):
        """Test on_posture_corrected calls WindowsNotifier."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger posture corrected event
        event_data = {
            'message': '✓ Good posture restored! Nice work!',
            'previous_duration': 650,
            'timestamp': '2025-01-04T10:40:00'
        }
        client.on_posture_corrected(event_data)

        # Verify notifier called
        mock_notifier.show_posture_corrected.assert_called_once()

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_posture_corrected_without_notifier(self, mock_client_class):
        """Test on_posture_corrected handles missing notifier gracefully."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        # No notifier provided
        client = SocketIOClient("http://localhost:5000", mock_tray, notifier=None)

        # Should not raise exception
        event_data = {
            'message': '✓ Good posture restored!',
            'previous_duration': 650,
            'timestamp': '2025-01-04T10:40:00'
        }
        client.on_posture_corrected(event_data)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_posture_corrected_defensive_extraction(self, mock_client_class):
        """Test on_posture_corrected handles missing 'previous_duration' field."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Missing 'previous_duration' field (optional analytics field)
        event_data = {'message': 'Test', 'timestamp': '2025-01-04T10:40:00'}
        client.on_posture_corrected(event_data)

        # Should not raise exception, still call notifier
        mock_notifier.show_posture_corrected.assert_called_once()


class TestSocketIOErrorHandling:
    """Test error event handling and defensive extraction."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_error_clears_emit_flag(self, mock_client_class):
        """Test on_error clears _emit_in_progress flag for retry.

        Note: MessageBox UI testing requires Windows environment.
        This test verifies enterprise-grade error handling: clearing
        the emit flag allows user to retry after backend error.
        """
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray._emit_in_progress = True

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Trigger error event
        error_data = {
            'message': 'Monitoring controls unavailable - camera service not started...'
        }
        client.on_error(error_data)

        # Verify _emit_in_progress flag cleared (critical for retry)
        assert mock_tray._emit_in_progress is False

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_error_defensive_extraction(self, mock_client_class):
        """Test on_error handles missing 'message' field."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Missing 'message' field (should default to 'Unknown error')
        error_data = {}

        # Should not raise exception
        client.on_error(error_data)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_monitoring_status_defensive_extraction(self, mock_client_class):
        """Test on_monitoring_status handles missing 'monitoring_active' field."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Missing 'monitoring_active' field (defaults to True)
        status_data = {}
        client.on_monitoring_status(status_data)

        # Should default to True (connected state)
        assert mock_tray.monitoring_active is True
        mock_tray.update_icon_state.assert_called_once_with('connected')

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_monitoring_status_clears_emit_flag(self, mock_client_class):
        """Test on_monitoring_status clears _emit_in_progress flag."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray._emit_in_progress = True
        mock_tray.update_icon_state = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Trigger monitoring status event
        client.on_monitoring_status({'monitoring_active': True})

        # Verify flag cleared
        assert mock_tray._emit_in_progress is False


class TestSocketIOTooltipUpdates:
    """Test tooltip update thread lifecycle and API calls."""

    @patch('app.windows_client.socketio_client.threading.Thread')
    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_connect_starts_tooltip_thread(self, mock_client_class, mock_thread_class):
        """Test on_connect starts tooltip update thread."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Reset mock from __init__ thread creation
        mock_thread_class.reset_mock()

        client.on_connect()

        # Verify thread started (2 threads: stats fetch + tooltip updater)
        assert mock_thread_class.call_count == 2

        # Verify tooltip updater thread created with correct args
        calls = mock_thread_class.call_args_list
        tooltip_thread_call = [c for c in calls if 'TooltipUpdater' in str(c)]
        assert len(tooltip_thread_call) == 1

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_disconnect_stops_tooltip_thread(self, mock_client_class):
        """Test on_disconnect stops tooltip update thread."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_tray.update_tooltip = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Start tooltip thread
        client._start_tooltip_update_thread()
        assert client._tooltip_thread is not None
        assert client._tooltip_thread.is_alive()

        # Disconnect should stop thread
        client.on_disconnect()

        # Verify stop event set
        assert client._tooltip_update_stop.is_set()

    @patch('app.windows_client.socketio_client.requests.get')
    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_update_tooltip_from_api_success(self, mock_client_class, mock_get):
        """Test _update_tooltip_from_api with successful API call."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_tooltip = Mock()

        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'posture_score': 85.0,
            'good_duration_seconds': 7200,
            'bad_duration_seconds': 1800,
            'total_events': 42
        }
        mock_get.return_value = mock_response

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client._update_tooltip_from_api()

        # Wait for background thread to complete
        time.sleep(0.1)

        # Verify API called with timeout
        mock_get.assert_called_once_with(
            "http://localhost:5000/api/stats/today",
            timeout=5
        )

        # Verify tooltip updated
        mock_tray.update_tooltip.assert_called_once()

    @patch('app.windows_client.socketio_client.requests.get')
    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_update_tooltip_from_api_failure(self, mock_client_class, mock_get):
        """Test _update_tooltip_from_api handles API failure gracefully."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        # Mock API failure (timeout)
        mock_get.side_effect = Exception("Connection timeout")

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Should not raise exception
        client._update_tooltip_from_api()

        # Wait for background thread to complete
        time.sleep(0.1)

    @patch('app.windows_client.socketio_client.requests.get')
    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_update_tooltip_from_api_4xx_error(self, mock_client_class, mock_get):
        """Test _update_tooltip_from_api handles HTTP 4xx errors."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_tooltip = Mock()

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client._update_tooltip_from_api()

        # Wait for background thread to complete
        time.sleep(0.1)

        # Should not update tooltip on 4xx error
        mock_tray.update_tooltip.assert_not_called()


class TestSocketIOConnectionNotifications:
    """Test connection status notifications (Story 7.2 integration)."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_connect_shows_connection_notification(self, mock_client_class):
        """Test on_connect shows 'Connected' notification."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)
        client.on_connect()

        # Verify connection notification shown
        mock_notifier.show_connection_status.assert_called_once_with(connected=True)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_disconnect_shows_disconnection_notification(self, mock_client_class):
        """Test on_disconnect shows 'Disconnected' notification."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_tray.update_tooltip = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)
        client.on_disconnect()

        # Verify disconnection notification shown
        mock_notifier.show_connection_status.assert_called_once_with(connected=False)


class TestSocketIOEventHandlerRegistration:
    """Test that all 6 event handlers are registered (Story 7.3)."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_all_event_handlers_registered(self, mock_client_class):
        """Test all 6 event handlers registered on init."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Verify all 6 event handlers registered
        assert mock_sio.on.call_count == 6

        # Verify specific handlers
        mock_sio.on.assert_any_call('connect', client.on_connect)
        mock_sio.on.assert_any_call('disconnect', client.on_disconnect)
        mock_sio.on.assert_any_call('monitoring_status', client.on_monitoring_status)
        mock_sio.on.assert_any_call('error', client.on_error)
        mock_sio.on.assert_any_call('alert_triggered', client.on_alert_triggered)
        mock_sio.on.assert_any_call('posture_corrected', client.on_posture_corrected)


class TestSocketIOThreadSafety:
    """Test thread-safe operations and graceful shutdown."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_disconnect_stops_tooltip_thread_gracefully(self, mock_client_class):
        """Test disconnect stops tooltip thread without blocking."""
        mock_sio = Mock()
        mock_sio.connected = True
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Start tooltip thread
        client._start_tooltip_update_thread()
        assert client._tooltip_thread.is_alive()

        # Disconnect should not block
        client.disconnect()

        # Verify stop event set (thread will exit on next loop)
        assert client._tooltip_update_stop.is_set()

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_tooltip_thread_is_daemon(self, mock_client_class):
        """Test tooltip thread is daemon (terminates with app)."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client._start_tooltip_update_thread()

        # Verify thread is daemon
        assert client._tooltip_thread.daemon is True

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_multiple_tooltip_thread_starts_no_duplicate(self, mock_client_class):
        """Test starting tooltip thread multiple times doesn't create duplicates."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Start thread twice
        client._start_tooltip_update_thread()
        first_thread = client._tooltip_thread

        client._start_tooltip_update_thread()
        second_thread = client._tooltip_thread

        # Should be same thread (no duplicate)
        assert first_thread is second_thread
        assert threading.active_count() >= 1  # At least main thread


class TestSocketIOEnterpriseGradeEdgeCases:
    """Test enterprise-grade edge cases and error handling."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_connect_emits_request_status(self, mock_client_class):
        """Test on_connect emits request_status to get initial monitoring state."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)
        client.on_connect()

        # Verify request_status emitted
        mock_sio.emit.assert_any_call('request_status')

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_connect_request_status_failure_handled(self, mock_client_class):
        """Test on_connect handles request_status emission failure gracefully."""
        mock_sio = Mock()
        mock_sio.emit.side_effect = Exception("Connection lost")
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Should not raise exception
        client.on_connect()

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_tray_manager_without_update_icon_state(self, mock_client_class):
        """Test graceful degradation if TrayManager lacks update_icon_state."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio

        # TrayManager without update_icon_state method (but has update_tooltip)
        # Testing hasattr() checks in SocketIOClient
        mock_tray = Mock()
        delattr(mock_tray, 'update_icon_state')

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Should not raise AttributeError
        client.on_connect()
        client.on_disconnect()
        client.on_monitoring_status({'monitoring_active': True})

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_malformed_json_in_event_data(self, mock_client_class):
        """Test handling of malformed event data (defensive extraction)."""
        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Test all event handlers with empty dict
        client.on_monitoring_status({})
        client.on_error({})
        client.on_alert_triggered({})
        client.on_posture_corrected({})

        # Should not raise exceptions
        assert True

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_disconnect_error_handling(self, mock_client_class):
        """Test disconnect handles errors gracefully."""
        mock_sio = Mock()
        mock_sio.connected = True
        mock_sio.disconnect.side_effect = Exception("Disconnect failed")
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray)

        # Should not raise exception
        client.disconnect()
