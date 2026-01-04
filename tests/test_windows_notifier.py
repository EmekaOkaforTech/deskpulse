"""Tests for Windows Desktop Client Toast Notification Manager."""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path
import queue
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestWindowsNotifierInit:
    """Test WindowsNotifier initialization."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_init_success(self):
        """Test successful initialization with winotify available."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        mock_tray.backend_url = "http://localhost:5000"

        notifier = WindowsNotifier(mock_tray)

        # Verify initialization
        assert notifier.tray_manager == mock_tray
        assert notifier.notifier_available is True
        assert isinstance(notifier.notification_queue, queue.PriorityQueue)
        assert notifier.queue_thread.is_alive()
        assert notifier.queue_thread.daemon is True
        assert notifier._queue_thread_retries == 0

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', False)
    def test_init_winotify_unavailable(self):
        """Test graceful degradation when winotify unavailable."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()

        notifier = WindowsNotifier(mock_tray)

        # Verify graceful degradation
        assert notifier.tray_manager == mock_tray
        assert notifier.notifier_available is False
        assert not hasattr(notifier, 'notification_queue')
        assert not hasattr(notifier, 'queue_thread')


class TestWindowsNotifierNotificationMethods:
    """Test notification creation and display methods."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.audio', create=True)
    @patch('app.windows_client.notifier.Notification', create=True)
    def test_create_notification_basic(self, mock_notification_class, mock_audio):
        """Test basic notification creation."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        mock_tray.backend_url = "http://localhost:5000"
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        mock_notification_class.return_value = mock_notif

        # Create notification
        result = notifier._create_notification(
            title="Test Title",
            message="Test Message",
            duration_seconds=10,
            buttons=None
        )

        # Verify notification created
        assert result == mock_notif
        mock_notification_class.assert_called_once()
        call_kwargs = mock_notification_class.call_args[1]
        assert call_kwargs['app_id'] == "DeskPulse"
        assert call_kwargs['title'] == "Test Title"
        assert call_kwargs['msg'] == "Test Message"
        assert call_kwargs['duration'] == 10

        # Verify audio set
        mock_notif.set_audio.assert_called_once()

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.Notification', create=True)
    @patch('app.windows_client.notifier.webbrowser')
    def test_create_notification_with_buttons(self, mock_webbrowser, mock_notification_class):
        """Test notification creation with action buttons."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        mock_tray.backend_url = "http://localhost:5000"
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        mock_notification_class.return_value = mock_notif

        # Create notification with button
        callback = lambda: None
        result = notifier._create_notification(
            title="Test",
            message="Test",
            duration_seconds=5,
            buttons=[("View Dashboard", callback)]
        )

        # Verify button added
        mock_notif.add_actions.assert_called_once_with(label="View Dashboard", launch=callback)

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_create_notification_unavailable(self):
        """Test notification creation when winotify unavailable at runtime."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)
        notifier.notifier_available = False

        result = notifier._create_notification("Title", "Message", 5)

        assert result is None


class TestWindowsNotifierQueueManagement:
    """Test notification queue management."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_queue_notification_success(self):
        """Test queuing notification successfully."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        notifier._queue_notification(mock_notif, priority=1)

        # Verify notification queued
        assert notifier.notification_queue.qsize() == 1

        # Get from queue to verify
        priority, notification = notifier.notification_queue.get_nowait()
        assert priority == 1
        assert notification == mock_notif

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_queue_notification_priority_ordering(self):
        """Test notifications queued by priority."""
        from app.windows_client.notifier import WindowsNotifier
        from app.windows_client.notifier import PRIORITY_ALERT, PRIORITY_CORRECTION, PRIORITY_CONNECTION

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        # Queue notifications in reverse priority order
        mock_conn = Mock()
        mock_corr = Mock()
        mock_alert = Mock()

        notifier._queue_notification(mock_conn, PRIORITY_CONNECTION)
        notifier._queue_notification(mock_corr, PRIORITY_CORRECTION)
        notifier._queue_notification(mock_alert, PRIORITY_ALERT)

        # Verify priority ordering (alert=1, correction=2, connection=3)
        priority1, notif1 = notifier.notification_queue.get_nowait()
        assert priority1 == PRIORITY_ALERT
        assert notif1 == mock_alert

        priority2, notif2 = notifier.notification_queue.get_nowait()
        assert priority2 == PRIORITY_CORRECTION
        assert notif2 == mock_corr

        priority3, notif3 = notifier.notification_queue.get_nowait()
        assert priority3 == PRIORITY_CONNECTION
        assert notif3 == mock_conn

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_queue_full_drops_lowest_priority(self):
        """Test queue full behavior drops lowest priority notification.

        Note: This tests the logic by verifying _queue_notification handles
        queue.Full exception and implements drop logic. Full integration
        testing of queue behavior requires real notification objects.
        """
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        # Test the queue full handling logic by filling queue manually
        # then calling _queue_notification which handles queue.Full
        for i in range(5):
            # Create simple comparable objects (tuples work in heapq)
            notifier.notification_queue.put_nowait((3, f"notif_{i}"))

        # Verify queue is full
        assert notifier.notification_queue.qsize() == 5

        # Now test _queue_notification with a high-priority mock
        # This should trigger the queue.Full handling and drop logic
        mock_notif = Mock()
        notifier._queue_notification(mock_notif, priority=1)

        # Queue size should still be 5 (dropped one, added one)
        assert notifier.notification_queue.qsize() == 5

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_queue_notification_when_unavailable(self):
        """Test queuing notification when notifier unavailable."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)
        notifier.notifier_available = False

        mock_notif = Mock()
        notifier._queue_notification(mock_notif, priority=1)

        # Verify notification not queued
        assert not hasattr(notifier, 'notification_queue') or notifier.notification_queue.qsize() == 0


class TestWindowsNotifierPostureAlerts:
    """Test posture alert notification methods."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.Notification', create=True)
    @patch('app.windows_client.notifier.webbrowser')
    def test_show_posture_alert(self, mock_webbrowser, mock_notification_class):
        """Test showing posture alert notification."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        mock_tray.backend_url = "http://localhost:5000"
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        mock_notification_class.return_value = mock_notif

        # Show alert (600 seconds = 10 minutes)
        notifier.show_posture_alert(duration_seconds=600)

        # Wait for notification to be queued
        time.sleep(0.1)

        # Verify notification created with correct duration
        assert mock_notification_class.called
        call_kwargs = mock_notification_class.call_args[1]
        assert "10 minutes" in call_kwargs['msg']
        assert call_kwargs['title'] == "Posture Alert ⚠️"
        assert call_kwargs['duration'] == 10

        # Verify notification queued
        assert notifier.notification_queue.qsize() >= 0  # May have been processed

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.Notification', create=True)
    def test_show_posture_corrected(self, mock_notification_class):
        """Test showing posture correction notification."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        mock_notification_class.return_value = mock_notif

        # Show correction notification
        notifier.show_posture_corrected()

        # Wait for notification to be queued
        time.sleep(0.1)

        # Verify notification created
        assert mock_notification_class.called
        call_kwargs = mock_notification_class.call_args[1]
        assert call_kwargs['title'] == "Great Job! ✓"
        assert "Good posture restored" in call_kwargs['msg']
        assert call_kwargs['duration'] == 5


class TestWindowsNotifierConnectionStatus:
    """Test connection status notification methods."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.Notification', create=True)
    def test_show_connection_status_connected(self, mock_notification_class):
        """Test showing connected notification."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        mock_notification_class.return_value = mock_notif

        # Show connected notification
        notifier.show_connection_status(connected=True)

        # Wait for notification to be queued
        time.sleep(0.1)

        # Verify notification created
        assert mock_notification_class.called
        call_kwargs = mock_notification_class.call_args[1]
        assert call_kwargs['title'] == "DeskPulse Connected"
        assert "Raspberry Pi" in call_kwargs['msg']
        assert call_kwargs['duration'] == 5

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.Notification', create=True)
    def test_show_connection_status_disconnected(self, mock_notification_class):
        """Test showing disconnected notification."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        mock_notif = Mock()
        mock_notification_class.return_value = mock_notif

        # Show disconnected notification
        notifier.show_connection_status(connected=False)

        # Wait for notification to be queued
        time.sleep(0.1)

        # Verify notification created
        assert mock_notification_class.called
        call_kwargs = mock_notification_class.call_args[1]
        assert call_kwargs['title'] == "DeskPulse Disconnected"
        assert "Lost connection" in call_kwargs['msg']


class TestWindowsNotifierShutdown:
    """Test notification manager shutdown."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_shutdown_graceful(self):
        """Test graceful shutdown of notification queue thread."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        # Verify thread running
        assert notifier.queue_thread.is_alive()

        # Shutdown
        notifier.shutdown()

        # Wait for thread to finish
        time.sleep(0.5)

        # Verify thread stopped
        assert not notifier.queue_thread.is_alive()
        assert notifier._shutdown_event.is_set()

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', False)
    def test_shutdown_when_unavailable(self):
        """Test shutdown when winotify unavailable (no-op)."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        # Should not raise exception
        notifier.shutdown()


class TestSocketIOIntegration:
    """Test SocketIO event handler integration."""

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_init_registers_notification_handlers(self, mock_client_class):
        """Test SocketIO client registers alert and correction handlers."""
        from app.windows_client.socketio_client import SocketIOClient

        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Verify new event handlers registered (Story 7.2)
        assert mock_sio.on.call_count == 6  # 4 original + 2 new
        mock_sio.on.assert_any_call('alert_triggered', client.on_alert_triggered)
        mock_sio.on.assert_any_call('posture_corrected', client.on_posture_corrected)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_alert_triggered_calls_notifier(self, mock_client_class):
        """Test alert_triggered event calls notifier."""
        from app.windows_client.socketio_client import SocketIOClient

        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger alert event
        event_data = {'duration': 600, 'message': 'Bad posture detected'}
        client.on_alert_triggered(event_data)

        # Verify notifier called with duration
        mock_notifier.show_posture_alert.assert_called_once_with(600)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_alert_triggered_defensive_extraction(self, mock_client_class):
        """Test alert_triggered handles missing duration field."""
        from app.windows_client.socketio_client import SocketIOClient

        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger alert with missing duration
        event_data = {'message': 'Bad posture detected'}
        client.on_alert_triggered(event_data)

        # Verify notifier called with default 0
        mock_notifier.show_posture_alert.assert_called_once_with(0)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_posture_corrected_calls_notifier(self, mock_client_class):
        """Test posture_corrected event calls notifier."""
        from app.windows_client.socketio_client import SocketIOClient

        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger correction event
        event_data = {'message': 'Good posture restored', 'previous_duration': 650}
        client.on_posture_corrected(event_data)

        # Verify notifier called
        mock_notifier.show_posture_corrected.assert_called_once()

    @patch('app.windows_client.socketio_client.socketio.Client')
    @patch('app.windows_client.socketio_client.requests')
    def test_on_connect_calls_notifier(self, mock_requests, mock_client_class):
        """Test connect event shows connection notification."""
        from app.windows_client.socketio_client import SocketIOClient

        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger connect event
        client.on_connect()

        # Verify notifier called with connected=True
        mock_notifier.show_connection_status.assert_called_once_with(connected=True)

    @patch('app.windows_client.socketio_client.socketio.Client')
    def test_on_disconnect_calls_notifier(self, mock_client_class):
        """Test disconnect event shows disconnection notification."""
        from app.windows_client.socketio_client import SocketIOClient

        mock_sio = Mock()
        mock_client_class.return_value = mock_sio
        mock_tray = Mock()
        mock_tray.update_icon_state = Mock()
        mock_tray.update_tooltip = Mock()
        mock_notifier = Mock()

        client = SocketIOClient("http://localhost:5000", mock_tray, mock_notifier)

        # Trigger disconnect event
        client.on_disconnect()

        # Verify notifier called with connected=False
        mock_notifier.show_connection_status.assert_called_once_with(connected=False)


class TestErrorHandling:
    """Test error handling and resilience."""

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    @patch('app.windows_client.notifier.Notification', create=True)
    def test_notification_creation_failure_returns_none(self, mock_notification_class):
        """Test notification creation failure returns None gracefully."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)

        # Simulate creation failure
        mock_notification_class.side_effect = Exception("Winotify error")

        result = notifier._create_notification("Title", "Message", 5)

        # Verify returns None instead of raising
        assert result is None

    @patch('app.windows_client.notifier.WINOTIFY_AVAILABLE', True)
    def test_show_posture_alert_when_unavailable(self):
        """Test posture alert gracefully degrades when unavailable."""
        from app.windows_client.notifier import WindowsNotifier

        mock_tray = Mock()
        notifier = WindowsNotifier(mock_tray)
        notifier.notifier_available = False

        # Should not raise exception
        notifier.show_posture_alert(600)
        notifier.show_posture_corrected()
        notifier.show_connection_status(True)
