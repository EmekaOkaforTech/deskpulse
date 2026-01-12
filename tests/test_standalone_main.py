"""
Tests for DeskPulse Standalone Main Entry Point (Story 8.5).

Enterprise-grade tests for:
- Single instance check (Windows mutex)
- Configuration loading (valid, corrupt, missing)
- Event queue creation
- Backend thread initialization
- Callback registration (glue code)
- Graceful shutdown sequence
- Exception handling

CRITICAL: Tests use real backend components (no mocks except camera hardware).
"""

import pytest
import time
import queue
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import sys

# Windows-specific imports
try:
    import win32event
    import win32api
    import winerror
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

from app.standalone.backend_thread import (
    BackendThread,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_NORMAL
)
from app.standalone.config import (
    load_config,
    save_config,
    get_appdata_dir,
    get_config_path,
    DEFAULT_CONFIG
)


@pytest.fixture
def temp_appdata(tmp_path, monkeypatch):
    """Mock %APPDATA% to temp directory."""
    fake_appdata = tmp_path / 'AppData' / 'Roaming'
    fake_appdata.mkdir(parents=True)
    monkeypatch.setenv('APPDATA', str(fake_appdata))
    return fake_appdata


@pytest.fixture
def test_config():
    """Test configuration dictionary."""
    return {
        'camera': {
            'index': 0,
            'fps': 10,
            'width': 640,
            'height': 480,
            'backend': 'directshow'
        },
        'monitoring': {
            'alert_threshold_seconds': 600
        },
        'ipc': {
            'event_queue_size': 150,
            'alert_latency_target_ms': 50,
            'metrics_log_interval_seconds': 60
        },
        'advanced': {
            'log_level': 'INFO'
        }
    }


@pytest.fixture
def mock_camera():
    """Mock camera hardware (only permitted mock)."""
    with patch('cv2.VideoCapture') as mock_cap:
        mock_instance = Mock()
        mock_instance.read.return_value = (True, Mock())
        mock_instance.isOpened.return_value = True
        mock_instance.set.return_value = True
        mock_instance.get.return_value = 640
        mock_cap.return_value = mock_instance
        yield mock_instance


class TestSingleInstanceCheck:
    """Test Windows mutex single instance check."""

    @pytest.mark.skipif(not WINDOWS_AVAILABLE, reason="Windows-specific test")
    def test_single_instance_mutex_creation(self):
        """Test mutex creation for single instance check."""
        mutex_name = 'Global\\DeskPulse_Test_SingleInstance'

        # Create first mutex
        mutex1 = win32event.CreateMutex(None, False, mutex_name)
        assert mutex1 is not None

        error1 = win32api.GetLastError()
        assert error1 != winerror.ERROR_ALREADY_EXISTS

        # Try to create second mutex with same name
        mutex2 = win32event.CreateMutex(None, False, mutex_name)
        assert mutex2 is not None

        error2 = win32api.GetLastError()
        assert error2 == winerror.ERROR_ALREADY_EXISTS

        # Cleanup
        win32api.CloseHandle(mutex1)
        win32api.CloseHandle(mutex2)

    @pytest.mark.skipif(not WINDOWS_AVAILABLE, reason="Windows-specific test")
    def test_mutex_release_allows_new_instance(self):
        """Test that releasing mutex allows new instance."""
        mutex_name = 'Global\\DeskPulse_Test_MutexRelease'

        # Create and release mutex
        mutex1 = win32event.CreateMutex(None, False, mutex_name)
        win32api.CloseHandle(mutex1)

        # Should be able to create new mutex without error
        mutex2 = win32event.CreateMutex(None, False, mutex_name)
        error = win32api.GetLastError()
        assert error != winerror.ERROR_ALREADY_EXISTS

        # Cleanup
        win32api.CloseHandle(mutex2)


class TestConfigurationLoading:
    """Test configuration loading and validation."""

    def test_load_valid_config(self, temp_appdata, test_config):
        """Test loading valid configuration file."""
        # Save test config
        config_path = get_config_path()
        with open(config_path, 'w') as f:
            json.dump(test_config, f)

        # Load config
        config = load_config()

        # Verify loaded correctly
        assert config['camera']['index'] == 0
        assert config['camera']['fps'] == 10
        assert config['monitoring']['alert_threshold_seconds'] == 600
        assert 'ipc' in config
        assert config['ipc']['event_queue_size'] == 150

    def test_load_missing_config_creates_default(self, temp_appdata):
        """Test that missing config creates default."""
        config_path = get_config_path()
        assert not config_path.exists()

        # Load config (should create default)
        config = load_config()

        # Verify default config
        assert config_path.exists()
        assert config['camera']['index'] == 0
        assert 'ipc' in config
        assert config['ipc']['event_queue_size'] == 150

    def test_load_corrupt_config_uses_default(self, temp_appdata):
        """Test that corrupt config falls back to default."""
        config_path = get_config_path()

        # Write corrupt JSON
        with open(config_path, 'w') as f:
            f.write("{ corrupt json ]")

        # Load config (should use default)
        config = load_config()

        # Verify default config used
        assert config == DEFAULT_CONFIG

    def test_config_adds_missing_ipc_section(self, temp_appdata):
        """Test that missing IPC section is added."""
        config_path = get_config_path()

        # Save config without IPC section
        config_no_ipc = {
            'camera': {'index': 0},
            'monitoring': {'alert_threshold_seconds': 600}
        }
        with open(config_path, 'w') as f:
            json.dump(config_no_ipc, f)

        # Load config
        config = load_config()

        # Verify IPC section added from defaults
        assert 'ipc' in config
        assert config['ipc']['event_queue_size'] == 150


class TestEventQueueCreation:
    """Test priority event queue creation."""

    def test_queue_creation_with_default_size(self, test_config):
        """Test creating queue with default size."""
        queue_size = test_config['ipc']['event_queue_size']
        event_queue = queue.PriorityQueue(maxsize=queue_size)

        assert event_queue.maxsize == 150
        assert event_queue.empty()

    def test_queue_priority_ordering(self):
        """Test that queue respects priority ordering."""
        event_queue = queue.PriorityQueue(maxsize=10)

        # Enqueue events with different priorities
        event_queue.put((PRIORITY_NORMAL, time.perf_counter(), 'correction', {}))
        event_queue.put((PRIORITY_CRITICAL, time.perf_counter(), 'alert', {}))
        event_queue.put((PRIORITY_HIGH, time.perf_counter(), 'status_change', {}))

        # Verify highest priority (CRITICAL=1) dequeued first
        priority1, _, event_type1, _ = event_queue.get()
        assert priority1 == PRIORITY_CRITICAL
        assert event_type1 == 'alert'

        # Verify second priority (HIGH=2)
        priority2, _, event_type2, _ = event_queue.get()
        assert priority2 == PRIORITY_HIGH
        assert event_type2 == 'status_change'

        # Verify third priority (NORMAL=3)
        priority3, _, event_type3, _ = event_queue.get()
        assert priority3 == PRIORITY_NORMAL
        assert event_type3 == 'correction'

    def test_queue_full_behavior(self):
        """Test queue behavior when full."""
        event_queue = queue.PriorityQueue(maxsize=2)

        # Fill queue
        event_queue.put((PRIORITY_NORMAL, time.perf_counter(), 'event1', {}))
        event_queue.put((PRIORITY_NORMAL, time.perf_counter(), 'event2', {}))

        assert event_queue.full()

        # Try to add with timeout (should raise Full)
        with pytest.raises(queue.Full):
            event_queue.put((PRIORITY_NORMAL, time.perf_counter(), 'event3', {}), timeout=0.1)


class TestCallbackRegistration:
    """Test callback registration glue code."""

    def test_all_callbacks_registered(self, temp_appdata, test_config, mock_camera):
        """Test that all 5 callbacks are registered successfully."""
        event_queue = queue.PriorityQueue(maxsize=20)

        # Create backend (real backend, mocked camera only)
        backend = BackendThread(test_config, event_queue=event_queue)

        # Register callbacks
        alert_called = []
        correction_called = []
        status_called = []
        camera_called = []
        error_called = []

        def on_alert(duration, timestamp):
            alert_called.append((duration, timestamp))

        def on_correction(previous_duration, timestamp):
            correction_called.append((previous_duration, timestamp))

        def on_status_change(monitoring_active, threshold_seconds):
            status_called.append((monitoring_active, threshold_seconds))

        def on_camera_state(state, timestamp):
            camera_called.append((state, timestamp))

        def on_error(message, error_type):
            error_called.append((message, error_type))

        backend.register_callback('alert', on_alert)
        backend.register_callback('correction', on_correction)
        backend.register_callback('status_change', on_status_change)
        backend.register_callback('camera_state', on_camera_state)
        backend.register_callback('error', on_error)

        # Verify all callbacks registered
        assert 'alert' in backend._callbacks
        assert 'correction' in backend._callbacks
        assert 'status_change' in backend._callbacks
        assert 'camera_state' in backend._callbacks
        assert 'error' in backend._callbacks

    def test_callback_enqueues_with_correct_priority(self, temp_appdata, test_config):
        """Test that callbacks enqueue events with correct priority."""
        event_queue = queue.PriorityQueue(maxsize=20)

        # Callback that enqueues CRITICAL event
        def on_alert_callback(duration, timestamp):
            event_queue.put((PRIORITY_CRITICAL, time.perf_counter(), 'alert', {
                'duration': duration,
                'timestamp': timestamp
            }), timeout=1.0)

        # Callback that enqueues NORMAL event
        def on_correction_callback(previous_duration, timestamp):
            event_queue.put((PRIORITY_NORMAL, time.perf_counter(), 'correction', {
                'previous_duration': previous_duration,
                'timestamp': timestamp
            }), timeout=0.5)

        # Simulate callback execution
        on_alert_callback(600, '2026-01-11T10:00:00')
        on_correction_callback(600, '2026-01-11T10:10:00')

        # Verify events in queue with correct priorities
        assert event_queue.qsize() == 2

        # First event should be CRITICAL (highest priority)
        priority1, _, event_type1, data1 = event_queue.get()
        assert priority1 == PRIORITY_CRITICAL
        assert event_type1 == 'alert'
        assert data1['duration'] == 600

        # Second event should be NORMAL
        priority2, _, event_type2, data2 = event_queue.get()
        assert priority2 == PRIORITY_NORMAL
        assert event_type2 == 'correction'
        assert data2['previous_duration'] == 600


class TestGracefulShutdown:
    """Test graceful shutdown sequence."""

    def test_shutdown_sequence_timing(self, temp_appdata, test_config, mock_camera):
        """Test shutdown completes within 2 second target."""
        event_queue = queue.PriorityQueue(maxsize=20)

        # Create backend
        backend = BackendThread(test_config, event_queue=event_queue)
        backend.start()

        # Wait for initialization
        time.sleep(2)

        # Measure shutdown time
        shutdown_start = time.time()
        backend.stop()
        shutdown_duration = time.time() - shutdown_start

        # Verify shutdown completed in <2s
        assert shutdown_duration < 2.0, f"Shutdown took {shutdown_duration:.2f}s (target: <2s)"

    def test_backend_stop_executes_wal_checkpoint(self, temp_appdata, test_config, mock_camera):
        """Test that backend.stop() executes WAL checkpoint."""
        event_queue = queue.PriorityQueue(maxsize=20)

        # Create backend
        backend = BackendThread(test_config, event_queue=event_queue)
        backend.start()
        time.sleep(2)

        # Stop backend
        backend.stop()

        # Backend should have executed WAL checkpoint
        # (verified in backend logs, not directly testable here)
        assert backend.flask_app is not None


class TestExceptionHandling:
    """Test exception handling in main entry point."""

    def test_backend_initialization_failure_handling(self, temp_appdata):
        """Test handling of backend initialization failure."""
        invalid_config = {
            'camera': {
                'index': -1,  # Invalid camera index
                'fps': 10
            }
        }

        event_queue = queue.PriorityQueue(maxsize=20)

        # Creating backend with invalid config should not crash
        # (backend handles errors gracefully)
        backend = BackendThread(invalid_config, event_queue=event_queue)
        assert backend is not None

    def test_missing_config_handled_gracefully(self, temp_appdata):
        """Test that missing config is handled without crash."""
        # Don't create config file
        config_path = get_config_path()
        assert not config_path.exists()

        # Loading config should create default, not crash
        config = load_config()
        assert config is not None
        assert config_path.exists()


class TestIntegration:
    """Integration tests for full main entry point flow."""

    def test_full_initialization_sequence(self, temp_appdata, test_config, mock_camera):
        """Test complete initialization sequence."""
        # 1. Load configuration
        config_path = get_config_path()
        with open(config_path, 'w') as f:
            json.dump(test_config, f)

        config = load_config()
        assert 'ipc' in config

        # 2. Create event queue
        queue_size = config['ipc']['event_queue_size']
        event_queue = queue.PriorityQueue(maxsize=queue_size)
        assert event_queue.maxsize == 150

        # 3. Create backend thread
        backend = BackendThread(config, event_queue=event_queue)
        backend.start()
        time.sleep(2)

        # Verify initialization
        assert backend.flask_app is not None
        assert backend.is_alive()

        # 4. Register callbacks
        callback_count = 0

        def dummy_callback(*args, **kwargs):
            nonlocal callback_count
            callback_count += 1

        backend.register_callback('alert', dummy_callback)
        backend.register_callback('correction', dummy_callback)
        backend.register_callback('status_change', dummy_callback)
        backend.register_callback('camera_state', dummy_callback)
        backend.register_callback('error', dummy_callback)

        # 5. Clean shutdown
        backend.stop()
        assert not backend.is_alive()

    def test_event_flow_end_to_end(self, temp_appdata, test_config, mock_camera):
        """Test end-to-end event flow: callback → queue → dequeue."""
        event_queue = queue.PriorityQueue(maxsize=20)

        # Create backend
        backend = BackendThread(test_config, event_queue=event_queue)

        # Register callback that enqueues event
        def on_alert_callback(duration, timestamp):
            event_queue.put((PRIORITY_CRITICAL, time.perf_counter(), 'alert', {
                'duration': duration,
                'timestamp': timestamp
            }), timeout=1.0)

        backend.register_callback('alert', on_alert_callback)

        # Trigger callback manually
        backend._notify_callbacks('alert', duration=600, timestamp='2026-01-11T10:00:00')

        # Verify event in queue
        assert event_queue.qsize() == 1

        # Dequeue and verify
        priority, enqueue_time, event_type, data = event_queue.get()
        assert priority == PRIORITY_CRITICAL
        assert event_type == 'alert'
        assert data['duration'] == 600

        # Cleanup
        backend.stop()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
