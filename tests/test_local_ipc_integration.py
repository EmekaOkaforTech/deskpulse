"""
Integration tests for Local IPC (Story 8.4).

ENTERPRISE REQUIREMENT: Tests use REAL backend components.
- Real callback registration system
- Real Flask app via create_app(standalone_mode=True)
- Real SQLite database in temp directory (WAL mode)
- Real alert manager
- Real analytics (PostureAnalytics)

Pattern Reference: test_standalone_integration.py (Story 8.1)
"""

import pytest
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import date

from app import create_app
from app.standalone.backend_thread import BackendThread
from app.standalone.config import get_database_path


@pytest.fixture
def temp_appdata(tmp_path, monkeypatch):
    """Create temporary %APPDATA% directory for testing."""
    fake_appdata = tmp_path / 'AppData' / 'Roaming'
    fake_appdata.mkdir(parents=True)
    monkeypatch.setenv('APPDATA', str(fake_appdata))
    return fake_appdata


@pytest.fixture
def test_config():
    """Test configuration - enterprise defaults."""
    return {
        'camera': {
            'index': 0,
            'fps': 10,
            'width': 640,
            'height': 480
        },
        'monitoring': {
            'alert_threshold_seconds': 600
        }
    }


@pytest.fixture
def backend_with_flask_app(temp_appdata, test_config):
    """
    Create BackendThread with initialized Flask app and alert manager.

    ENTERPRISE: Real Flask app, real database, real alert manager.
    Mocks only CV pipeline to avoid camera hardware dependency.
    """
    backend = BackendThread(test_config)

    # Initialize Flask app (same as backend_thread._run_backend)
    database_path = str(get_database_path())
    backend.flask_app = create_app(
        config_name='standalone',
        database_path=database_path,
        standalone_mode=True
    )

    # Initialize database
    with backend.flask_app.app_context():
        from app.extensions import init_db
        init_db(backend.flask_app)

    # Mock CV pipeline (avoid camera hardware)
    backend.cv_pipeline = Mock()
    backend.cv_pipeline.is_running.return_value = True

    # Create REAL alert manager (enterprise requirement)
    with backend.flask_app.app_context():
        from app.alerts.manager import AlertManager
        backend.cv_pipeline.alert_manager = AlertManager()

    yield backend

    # No cleanup needed (not started as thread)


class TestCallbackRegistration:
    """Test callback registration with real BackendThread."""

    def test_register_callback(self, test_config):
        """Test callback registration."""
        backend = BackendThread(test_config)
        callback = Mock()

        backend.register_callback('alert', callback)

        assert callback in backend._callbacks['alert']
        assert len(backend._callbacks['alert']) == 1

    def test_register_multiple_callbacks(self, test_config):
        """Test registering multiple callbacks for same event."""
        backend = BackendThread(test_config)
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)
        backend.register_callback('alert', callback3)

        assert len(backend._callbacks['alert']) == 3

    def test_unregister_callback(self, test_config):
        """Test unregistering specific callback."""
        backend = BackendThread(test_config)
        callback1 = Mock()
        callback2 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)

        backend.unregister_callback('alert', callback1)

        assert callback1 not in backend._callbacks['alert']
        assert callback2 in backend._callbacks['alert']

    def test_unregister_all_callbacks(self, test_config):
        """Test unregistering all callbacks."""
        backend = BackendThread(test_config)
        callback1 = Mock()
        callback2 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('correction', callback2)

        backend.unregister_all_callbacks()

        assert len(backend._callbacks) == 0


class TestCallbackInvocation:
    """Test callback invocation with real backend."""

    def test_notify_callbacks_invokes_registered_callbacks(self, test_config):
        """Test that _notify_callbacks invokes all registered callbacks."""
        backend = BackendThread(test_config)
        callback1 = Mock()
        callback2 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)

        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        callback1.assert_called_once_with(duration=600, timestamp='2026-01-10T12:00:00')
        callback2.assert_called_once_with(duration=600, timestamp='2026-01-10T12:00:00')

    def test_error_notification_triggers_callbacks(self, test_config):
        """Test error notification triggers error callbacks."""
        backend = BackendThread(test_config)
        error_callback = Mock()

        backend.register_callback('error', error_callback)
        backend.notify_error('Test error message', 'camera')

        error_callback.assert_called_once_with(message='Test error message', error_type='camera')


class TestDirectControlMethods:
    """Test direct control methods with real alert manager."""

    def test_pause_monitoring_triggers_status_change_callback(self, backend_with_flask_app):
        """Test pause_monitoring triggers status_change callback with real alert manager."""
        status_changes = []

        def on_status_change(monitoring_active, threshold_seconds):
            status_changes.append({
                'monitoring_active': monitoring_active,
                'threshold_seconds': threshold_seconds
            })

        backend_with_flask_app.register_callback('status_change', on_status_change)
        backend_with_flask_app.pause_monitoring()

        # Verify callback triggered
        assert len(status_changes) == 1
        assert status_changes[0]['monitoring_active'] == False
        assert status_changes[0]['threshold_seconds'] == 600

    def test_resume_monitoring_triggers_status_change_callback(self, backend_with_flask_app):
        """Test resume_monitoring triggers status_change callback with real alert manager."""
        status_changes = []

        def on_status_change(monitoring_active, threshold_seconds):
            status_changes.append({
                'monitoring_active': monitoring_active,
                'threshold_seconds': threshold_seconds
            })

        backend_with_flask_app.register_callback('status_change', on_status_change)

        # Pause then resume
        backend_with_flask_app.pause_monitoring()
        backend_with_flask_app.resume_monitoring()

        # Verify both callbacks triggered
        assert len(status_changes) == 2
        assert status_changes[0]['monitoring_active'] == False
        assert status_changes[1]['monitoring_active'] == True

    def test_get_today_stats_with_real_database(self, backend_with_flask_app):
        """Test get_today_stats() returns data from real PostureAnalytics."""
        stats = backend_with_flask_app.get_today_stats()

        # Should return dict from real PostureAnalytics.calculate_daily_stats()
        assert isinstance(stats, dict)
        assert 'date' in stats
        assert 'good_duration_seconds' in stats
        assert 'bad_duration_seconds' in stats
        assert 'posture_score' in stats

    def test_get_history_with_real_database(self, backend_with_flask_app):
        """Test get_history() returns data from real PostureAnalytics."""
        history = backend_with_flask_app.get_history()

        # Should return list from real PostureAnalytics.get_7_day_history()
        assert isinstance(history, list)
        assert len(history) == 7  # 7-day history


class TestCallbackExceptionHandling:
    """Test callback exception isolation."""

    def test_callback_exception_does_not_crash_backend(self, test_config):
        """Test that callback exceptions don't crash the backend."""
        backend = BackendThread(test_config)

        def failing_callback(**kwargs):
            raise ValueError("Test exception from callback")

        callback_after_exception = Mock()

        backend.register_callback('error', failing_callback)
        backend.register_callback('error', callback_after_exception)

        # Trigger error - should not raise exception
        backend.notify_error('Test error', 'test')

        # Second callback should have executed
        callback_after_exception.assert_called_once()

    def test_callback_exception_isolation(self, test_config):
        """Test that one callback failure doesn't prevent others from executing."""
        backend = BackendThread(test_config)
        callback1 = Mock()
        callback3 = Mock()

        def failing_callback(**kwargs):
            raise ValueError("Test exception")

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', failing_callback)
        backend.register_callback('alert', callback3)

        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        # callback1 and callback3 should still execute
        callback1.assert_called_once()
        callback3.assert_called_once()


class TestThreadSafety:
    """Test thread-safe callback operations."""

    def test_concurrent_callback_registration(self, test_config):
        """Test concurrent callback registration from multiple threads."""
        backend = BackendThread(test_config)
        callbacks = []

        def register_callbacks(thread_id):
            for i in range(10):
                callback = Mock()
                callbacks.append(callback)
                backend.register_callback('alert', callback)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_callbacks, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All 50 callbacks should be registered
        assert len(backend._callbacks['alert']) == 50

    def test_concurrent_callback_invocation(self, test_config):
        """Test concurrent callback invocation from multiple threads."""
        backend = BackendThread(test_config)
        invocation_count = {'count': 0}
        lock = threading.Lock()

        def counting_callback(**kwargs):
            with lock:
                invocation_count['count'] += 1

        backend.register_callback('alert', counting_callback)

        def trigger_callbacks():
            for _ in range(10):
                backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        threads = []
        for i in range(5):
            thread = threading.Thread(target=trigger_callbacks)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 5 threads * 10 invocations = 50 total
        assert invocation_count['count'] == 50


class TestWALCheckpoint:
    """Test WAL checkpoint on shutdown."""

    def test_wal_checkpoint_on_stop(self, backend_with_flask_app):
        """Test that stop() executes WAL checkpoint."""
        # This test verifies the checkpoint is called without errors
        # Real checkpoint validation requires database introspection

        backend_with_flask_app.stop()

        # Verify backend stopped cleanly (no exceptions)
        assert not backend_with_flask_app.running
