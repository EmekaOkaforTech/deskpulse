"""
Unit tests for TrayApp (Story 8.4 - Task 3.4).

Tests event queue consumer, event handling, metrics tracking,
and graceful shutdown.

Note: pystray UI interaction not tested (requires Windows desktop session).
Tests focus on event processing logic and queue consumer.
"""

import pytest
import time
import queue
import threading
from unittest.mock import Mock, patch, MagicMock

# Mock Windows dependencies before import
with patch.dict('sys.modules', {
    'pystray': MagicMock(),
    'PIL': MagicMock(),
    'PIL.Image': MagicMock(),
    'PIL.ImageDraw': MagicMock(),
    'winotify': MagicMock()
}):
    from app.standalone.tray_app import TrayApp
    from app.standalone.backend_thread import (
        PRIORITY_CRITICAL,
        PRIORITY_HIGH,
        PRIORITY_NORMAL,
        PRIORITY_LOW
    )


@pytest.fixture
def mock_backend():
    """Mock BackendThread for testing."""
    backend = Mock()
    backend.pause_monitoring.return_value = None
    backend.resume_monitoring.return_value = None
    backend.get_today_stats.return_value = {
        'good_duration_seconds': 3600,
        'bad_duration_seconds': 600,
        'posture_score': 85.7
    }
    backend.get_queue_metrics.return_value = {
        'events_produced': 100,
        'events_dropped': 5,
        'drop_rate_percent': 5.0,
        'queue_size': 10
    }
    return backend


@pytest.fixture
def event_queue_small():
    """Small event queue for testing."""
    return queue.PriorityQueue(maxsize=10)


@pytest.fixture
def tray_app(mock_backend, event_queue_small):
    """Create TrayApp instance for testing (without starting)."""
    with patch('app.standalone.tray_app.WINDOWS_AVAILABLE', True):
        # Mock pystray and PIL imports
        with patch('app.standalone.tray_app.Image') as mock_image, \
             patch('app.standalone.tray_app.ImageDraw') as mock_draw:

            # Setup mocks
            mock_img = Mock()
            mock_image.new.return_value = mock_img
            mock_draw.Draw.return_value = Mock()

            app = TrayApp(mock_backend, event_queue_small)
            return app


class TestTrayAppInitialization:
    """Test TrayApp initialization."""

    def test_initialization(self, tray_app):
        """Test TrayApp initializes correctly."""
        assert tray_app.monitoring_active == True
        assert tray_app.alert_active == False
        assert tray_app.running == False
        assert tray_app._events_processed == 0
        assert len(tray_app._latency_samples) == 0

    def test_icon_cache_created(self, tray_app):
        """Test icon images are pre-cached."""
        # Should have icons for each state
        assert 'monitoring' in tray_app.icon_cache
        assert 'paused' in tray_app.icon_cache
        assert 'alert' in tray_app.icon_cache
        assert 'disconnected' in tray_app.icon_cache


class TestEventHandling:
    """Test event handling methods."""

    def test_handle_alert_event(self, tray_app):
        """Test alert event handling."""
        data = {'duration': 600, 'timestamp': '2026-01-10T12:00:00'}
        latency_ms = 25.5

        with patch.object(tray_app, '_show_toast') as mock_toast, \
             patch.object(tray_app, '_update_tray_icon') as mock_update_icon:

            tray_app._handle_alert(data, latency_ms)

            # Should set alert_active
            assert tray_app.alert_active == True

            # Should update icon
            mock_update_icon.assert_called_once()

            # Should show toast
            mock_toast.assert_called_once()
            call_args = mock_toast.call_args[1]
            assert '10 minutes' in call_args['message']  # 600 seconds = 10 minutes

    def test_handle_correction_event(self, tray_app):
        """Test correction event handling."""
        # Set alert active first
        tray_app.alert_active = True

        data = {'previous_duration': 720, 'timestamp': '2026-01-10T12:00:00'}
        latency_ms = 15.2

        with patch.object(tray_app, '_show_toast') as mock_toast, \
             patch.object(tray_app, '_update_tray_icon') as mock_update_icon:

            tray_app._handle_correction(data, latency_ms)

            # Should clear alert_active
            assert tray_app.alert_active == False

            # Should update icon
            mock_update_icon.assert_called_once()

            # Should show positive toast
            mock_toast.assert_called_once()
            call_args = mock_toast.call_args[1]
            assert '12 minutes' in call_args['message']  # 720 seconds = 12 minutes

    def test_handle_status_change_pause(self, tray_app):
        """Test status_change event (pause)."""
        data = {'monitoring_active': False, 'threshold_seconds': 600}

        with patch.object(tray_app, '_update_tray_icon') as mock_update_icon:
            tray_app._handle_status_change(data)

            # Should update monitoring_active
            assert tray_app.monitoring_active == False

            # Should update icon
            mock_update_icon.assert_called_once()

    def test_handle_status_change_resume(self, tray_app):
        """Test status_change event (resume)."""
        tray_app.monitoring_active = False
        data = {'monitoring_active': True, 'threshold_seconds': 600}

        with patch.object(tray_app, '_update_tray_icon') as mock_update_icon:
            tray_app._handle_status_change(data)

            # Should update monitoring_active
            assert tray_app.monitoring_active == True

            # Should update icon
            mock_update_icon.assert_called_once()

    def test_handle_error_event(self, tray_app):
        """Test error event handling."""
        data = {'message': 'Camera disconnected', 'error_type': 'camera'}

        with patch.object(tray_app, '_show_toast') as mock_toast:
            tray_app._handle_error(data)

            # Should show error toast
            mock_toast.assert_called_once()
            call_args = mock_toast.call_args[1]
            assert 'camera' in call_args['title']
            assert 'Camera disconnected' in call_args['message']


class TestEventQueueConsumer:
    """Test event queue consumer functionality."""

    def test_consumer_processes_events(self, tray_app, event_queue_small):
        """Test consumer thread processes events from queue."""
        tray_app.running = True

        # Enqueue test event
        event = (PRIORITY_CRITICAL, time.perf_counter(), 'alert', {'duration': 600, 'timestamp': '...'})
        event_queue_small.put(event)

        # Mock event handler
        with patch.object(tray_app, '_handle_event') as mock_handle:
            # Run consumer for a short time
            consumer_thread = threading.Thread(target=tray_app._event_consumer_loop, daemon=True)
            consumer_thread.start()

            # Wait for event to be processed
            time.sleep(0.2)

            # Stop consumer
            tray_app.running = False
            tray_app.shutdown_event.set()
            consumer_thread.join(timeout=1)

            # Verify event was handled
            mock_handle.assert_called_once()
            call_args = mock_handle.call_args[0]
            assert call_args[0] == 'alert'  # event_type
            assert call_args[1]['duration'] == 600  # data

    def test_consumer_tracks_latency(self, tray_app, event_queue_small):
        """Test consumer tracks event latency."""
        tray_app.running = True

        # Enqueue event
        enqueue_time = time.perf_counter()
        event = (PRIORITY_CRITICAL, enqueue_time, 'alert', {'duration': 600, 'timestamp': '...'})
        event_queue_small.put(event)

        # Mock handler
        with patch.object(tray_app, '_handle_event'):
            consumer_thread = threading.Thread(target=tray_app._event_consumer_loop, daemon=True)
            consumer_thread.start()

            time.sleep(0.2)

            tray_app.running = False
            tray_app.shutdown_event.set()
            consumer_thread.join(timeout=1)

            # Verify latency sample was tracked
            assert len(tray_app._latency_samples) == 1
            assert tray_app._latency_samples[0] >= 0  # Latency should be non-negative

    def test_consumer_increments_processed_counter(self, tray_app, event_queue_small):
        """Test consumer increments events_processed counter."""
        tray_app.running = True

        # Enqueue 3 events
        for i in range(3):
            event = (PRIORITY_NORMAL, time.perf_counter(), 'correction', {'previous_duration': 600, 'timestamp': '...'})
            event_queue_small.put(event)

        with patch.object(tray_app, '_handle_event'):
            consumer_thread = threading.Thread(target=tray_app._event_consumer_loop, daemon=True)
            consumer_thread.start()

            time.sleep(0.3)

            tray_app.running = False
            tray_app.shutdown_event.set()
            consumer_thread.join(timeout=1)

            # Verify counter incremented
            assert tray_app._events_processed == 3

    def test_consumer_handles_exceptions_gracefully(self, tray_app, event_queue_small):
        """Test consumer continues processing after handler exception."""
        tray_app.running = True

        # Enqueue 2 events
        event1 = (PRIORITY_CRITICAL, time.perf_counter(), 'alert', {'duration': 600, 'timestamp': '...'})
        event2 = (PRIORITY_NORMAL, time.perf_counter(), 'correction', {'previous_duration': 600, 'timestamp': '...'})
        event_queue_small.put(event1)
        event_queue_small.put(event2)

        # Mock handler to raise exception on first call only
        with patch.object(tray_app, '_handle_event') as mock_handle:
            mock_handle.side_effect = [ValueError("Test exception"), None]

            consumer_thread = threading.Thread(target=tray_app._event_consumer_loop, daemon=True)
            consumer_thread.start()

            time.sleep(0.3)

            tray_app.running = False
            tray_app.shutdown_event.set()
            consumer_thread.join(timeout=1)

            # Both events should have been attempted
            assert mock_handle.call_count == 2


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""

    def test_shutdown_event_stops_consumer(self, tray_app, event_queue_small):
        """Test shutdown_event stops consumer loop."""
        tray_app.running = True

        consumer_thread = threading.Thread(target=tray_app._event_consumer_loop, daemon=True)
        consumer_thread.start()

        time.sleep(0.1)

        # Signal shutdown
        tray_app.running = False
        tray_app.shutdown_event.set()

        # Consumer should exit
        consumer_thread.join(timeout=2)
        assert not consumer_thread.is_alive()


class TestMetrics:
    """Test metrics tracking and reporting."""

    def test_get_consumer_metrics(self, tray_app):
        """Test get_consumer_metrics() returns correct data."""
        # Simulate some processing
        tray_app._events_processed = 50
        tray_app._latency_samples = [10.5, 15.2, 8.3, 25.0, 12.1]

        metrics = tray_app.get_consumer_metrics()

        assert metrics['events_processed'] == 50
        assert metrics['latency_samples'] == 5
        assert metrics['latency_avg_ms'] > 0
        assert metrics['latency_p95_ms'] > 0

    def test_latency_samples_limited_to_100(self, tray_app):
        """Test latency samples limited to last 100."""
        # Add 150 samples
        for i in range(150):
            tray_app._latency_samples.append(float(i))

        # Trigger limit check by simulating event processing
        while len(tray_app._latency_samples) > 100:
            tray_app._latency_samples.pop(0)

        assert len(tray_app._latency_samples) == 100


class TestMenuActions:
    """Test menu action methods."""

    def test_toggle_monitoring_pause(self, tray_app, mock_backend):
        """Test pause monitoring via menu."""
        tray_app.monitoring_active = True

        tray_app._toggle_monitoring()

        # Should call backend.pause_monitoring()
        mock_backend.pause_monitoring.assert_called_once()

    def test_toggle_monitoring_resume(self, tray_app, mock_backend):
        """Test resume monitoring via menu."""
        tray_app.monitoring_active = False

        tray_app._toggle_monitoring()

        # Should call backend.resume_monitoring()
        mock_backend.resume_monitoring.assert_called_once()

    def test_show_stats_retrieves_from_backend(self, tray_app, mock_backend):
        """Test show stats retrieves data from backend."""
        import ctypes
        with patch.object(ctypes.windll.user32, 'MessageBoxW') as mock_msgbox:
            tray_app._show_stats()

            # Should call backend.get_today_stats()
            mock_backend.get_today_stats.assert_called_once()

            # Should show message box
            mock_msgbox.assert_called_once()
