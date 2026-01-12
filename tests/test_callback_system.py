"""
Unit tests for BackendThread callback registration system (Story 8.4).

Tests callback registration, unregistration, invocation, exception isolation,
and thread safety.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch
from app.standalone.backend_thread import BackendThread


class TestCallbackRegistration:
    """Test callback registration and unregistration."""

    def test_register_single_callback(self):
        """Test registering a single callback for an event type."""
        backend = BackendThread({'camera': {}})
        callback = Mock()

        backend.register_callback('alert', callback)

        assert 'alert' in backend._callbacks
        assert callback in backend._callbacks['alert']
        assert len(backend._callbacks['alert']) == 1

    def test_register_multiple_callbacks_same_event(self):
        """Test registering multiple callbacks for the same event type."""
        backend = BackendThread({'camera': {}})
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)
        backend.register_callback('alert', callback3)

        assert len(backend._callbacks['alert']) == 3
        assert callback1 in backend._callbacks['alert']
        assert callback2 in backend._callbacks['alert']
        assert callback3 in backend._callbacks['alert']

    def test_register_callbacks_different_events(self):
        """Test registering callbacks for different event types."""
        backend = BackendThread({'camera': {}})
        alert_callback = Mock()
        correction_callback = Mock()
        status_callback = Mock()

        backend.register_callback('alert', alert_callback)
        backend.register_callback('correction', correction_callback)
        backend.register_callback('status_change', status_callback)

        assert len(backend._callbacks['alert']) == 1
        assert len(backend._callbacks['correction']) == 1
        assert len(backend._callbacks['status_change']) == 1

    def test_unregister_callback(self):
        """Test unregistering a specific callback."""
        backend = BackendThread({'camera': {}})
        callback1 = Mock()
        callback2 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)

        backend.unregister_callback('alert', callback1)

        assert callback1 not in backend._callbacks['alert']
        assert callback2 in backend._callbacks['alert']
        assert len(backend._callbacks['alert']) == 1

    def test_unregister_nonexistent_callback(self):
        """Test unregistering a callback that wasn't registered (no error)."""
        backend = BackendThread({'camera': {}})
        callback = Mock()

        # Should not raise exception
        backend.unregister_callback('alert', callback)

    def test_unregister_all_callbacks(self):
        """Test unregistering all callbacks."""
        backend = BackendThread({'camera': {}})
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('correction', callback2)
        backend.register_callback('status_change', callback3)

        backend.unregister_all_callbacks()

        assert len(backend._callbacks) == 0


class TestCallbackInvocation:
    """Test callback invocation with correct parameters."""

    def test_notify_callbacks_invokes_registered_callbacks(self):
        """Test that _notify_callbacks invokes all registered callbacks."""
        backend = BackendThread({'camera': {}})
        callback1 = Mock()
        callback2 = Mock()

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)

        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        callback1.assert_called_once_with(duration=600, timestamp='2026-01-10T12:00:00')
        callback2.assert_called_once_with(duration=600, timestamp='2026-01-10T12:00:00')

    def test_notify_callbacks_with_no_registered_callbacks(self):
        """Test that _notify_callbacks handles no registered callbacks gracefully."""
        backend = BackendThread({'camera': {}})

        # Should not raise exception
        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

    def test_notify_callbacks_execution_order_fifo(self):
        """Test that callbacks execute in registration order (FIFO)."""
        backend = BackendThread({'camera': {}})
        execution_order = []

        def callback1(**kwargs):
            execution_order.append(1)

        def callback2(**kwargs):
            execution_order.append(2)

        def callback3(**kwargs):
            execution_order.append(3)

        backend.register_callback('alert', callback1)
        backend.register_callback('alert', callback2)
        backend.register_callback('alert', callback3)

        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        assert execution_order == [1, 2, 3]

    def test_notify_callbacks_with_different_event_types(self):
        """Test that callbacks are event-type specific."""
        backend = BackendThread({'camera': {}})
        alert_callback = Mock()
        correction_callback = Mock()

        backend.register_callback('alert', alert_callback)
        backend.register_callback('correction', correction_callback)

        # Trigger alert
        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        alert_callback.assert_called_once()
        correction_callback.assert_not_called()


class TestCallbackExceptionIsolation:
    """Test callback exception isolation (failures don't crash backend)."""

    def test_callback_exception_does_not_crash_backend(self):
        """Test that callback exceptions are caught and logged."""
        backend = BackendThread({'camera': {}})

        def failing_callback(**kwargs):
            raise ValueError("Test exception")

        backend.register_callback('alert', failing_callback)

        # Should not raise exception
        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

    def test_callback_exception_does_not_prevent_other_callbacks(self):
        """Test that one callback failure doesn't prevent others from executing."""
        backend = BackendThread({'camera': {}})
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

    def test_callback_exception_logged(self, caplog):
        """Test that callback exceptions are logged."""
        backend = BackendThread({'camera': {}})

        def failing_callback(**kwargs):
            raise ValueError("Test exception from callback")

        backend.register_callback('alert', failing_callback)

        with caplog.at_level('ERROR'):
            backend._notify_callbacks('alert', duration=600, timestamp='2026-01-10T12:00:00')

        # Check that exception was logged
        assert any("Callback exception" in record.message for record in caplog.records)


class TestCallbackThreadSafety:
    """Test thread-safe callback registration and invocation."""

    def test_concurrent_callback_registration(self):
        """Test concurrent callback registration from multiple threads."""
        backend = BackendThread({'camera': {}})
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

    def test_concurrent_callback_invocation(self):
        """Test concurrent callback invocation from multiple threads."""
        backend = BackendThread({'camera': {}})
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

    def test_concurrent_register_and_unregister(self):
        """Test concurrent registration and unregistration doesn't crash."""
        backend = BackendThread({'camera': {}})
        callbacks = []

        def register_callbacks():
            for i in range(10):
                callback = Mock()
                callbacks.append(callback)
                backend.register_callback('alert', callback)

        def unregister_callbacks():
            time.sleep(0.01)  # Let some register first
            for callback in callbacks[:5]:  # Unregister first 5
                backend.unregister_callback('alert', callback)

        register_thread = threading.Thread(target=register_callbacks)
        unregister_thread = threading.Thread(target=unregister_callbacks)

        register_thread.start()
        unregister_thread.start()

        register_thread.join()
        unregister_thread.join()

        # At least some callbacks should remain registered
        assert len(backend._callbacks['alert']) >= 5


class TestErrorNotification:
    """Test error notification method."""

    def test_notify_error_triggers_callback(self):
        """Test that notify_error triggers error callbacks."""
        backend = BackendThread({'camera': {}})
        error_callback = Mock()

        backend.register_callback('error', error_callback)
        backend.notify_error('Test error message', 'camera')

        error_callback.assert_called_once_with(message='Test error message', error_type='camera')

    def test_notify_error_default_type(self):
        """Test notify_error with default error_type."""
        backend = BackendThread({'camera': {}})
        error_callback = Mock()

        backend.register_callback('error', error_callback)
        backend.notify_error('Test error')

        error_callback.assert_called_once_with(message='Test error', error_type='general')


class TestCallbackIntegrationWithPauseResume:
    """Test callbacks integrated with pause/resume monitoring."""

    def test_pause_monitoring_triggers_status_change_callback(self):
        """Test that pause_monitoring triggers status_change callback."""
        # This is a lightweight test - full integration test in test_local_ipc_integration.py
        backend = BackendThread({'camera': {}})
        status_callback = Mock()

        # Mock CV pipeline and alert manager
        backend.cv_pipeline = Mock()
        backend.flask_app = Mock()
        backend.flask_app.app_context.return_value.__enter__ = Mock()
        backend.flask_app.app_context.return_value.__exit__ = Mock()
        backend.cv_pipeline.alert_manager = Mock()
        backend.cv_pipeline.alert_manager.get_monitoring_status.return_value = {
            'threshold_seconds': 600
        }

        backend.register_callback('status_change', status_callback)
        backend.pause_monitoring()

        status_callback.assert_called_once_with(
            monitoring_active=False,
            threshold_seconds=600
        )

    def test_resume_monitoring_triggers_status_change_callback(self):
        """Test that resume_monitoring triggers status_change callback."""
        backend = BackendThread({'camera': {}})
        status_callback = Mock()

        # Mock CV pipeline and alert manager
        backend.cv_pipeline = Mock()
        backend.flask_app = Mock()
        backend.flask_app.app_context.return_value.__enter__ = Mock()
        backend.flask_app.app_context.return_value.__exit__ = Mock()
        backend.cv_pipeline.alert_manager = Mock()
        backend.cv_pipeline.alert_manager.get_monitoring_status.return_value = {
            'threshold_seconds': 600
        }

        backend.register_callback('status_change', status_callback)
        backend.resume_monitoring()

        status_callback.assert_called_once_with(
            monitoring_active=True,
            threshold_seconds=600
        )
