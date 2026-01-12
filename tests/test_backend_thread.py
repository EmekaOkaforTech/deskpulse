"""
Unit tests for Windows standalone backend thread.

Tests BackendThread lifecycle, error handling, and status methods.
Uses mocked components to avoid requiring actual hardware.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from app.standalone.backend_thread import (
    BackendThread,
    get_backend,
    start_backend,
    stop_backend
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
    """Test configuration."""
    return {
        'camera': {
            'index': 0,
            'fps': 10,
            'width': 640,
            'height': 480
        },
        'monitoring': {
            'alert_threshold_seconds': 600
        },
        'advanced': {
            'log_level': 'INFO'
        }
    }


@pytest.fixture
def mock_camera():
    """Mock WindowsCamera."""
    camera = Mock()
    camera.open.return_value = True
    camera.is_available.return_value = True
    camera.read.return_value = (True, Mock())
    return camera


@pytest.fixture
def mock_cv_pipeline():
    """Mock CVPipeline."""
    pipeline = Mock()
    pipeline.start.return_value = None
    pipeline.stop.return_value = None
    pipeline.is_running.return_value = True
    pipeline.camera = Mock()
    pipeline.camera.is_available.return_value = True
    pipeline.alert_manager = Mock()
    pipeline.alert_manager.get_monitoring_status.return_value = {
        'monitoring_active': True
    }
    return pipeline


@pytest.fixture
def mock_flask_app(temp_appdata):
    """Mock Flask app."""
    app = Mock()
    app.config = {}
    app.app_context = MagicMock()
    return app


class TestBackendThreadLifecycle:
    """Test BackendThread start/stop lifecycle."""

    def test_backend_thread_initialization(self, test_config):
        """Test BackendThread initialization."""
        backend = BackendThread(test_config)

        assert backend.config == test_config
        assert backend.running is False
        assert backend.thread is None
        assert backend.flask_app is None
        assert backend.cv_pipeline is None

    @patch('app.extensions.init_db')
    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_backend_thread_start_and_stop(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test BackendThread start and stop."""
        # Setup mocks
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline
        mock_init_db.return_value = None

        # Create and start backend
        backend = BackendThread(test_config)
        backend.start()

        # Wait for thread to initialize
        time.sleep(1)

        # Verify started
        assert backend.is_running()
        assert backend.thread is not None
        assert backend.thread.is_alive()

        # Stop backend
        backend.stop()

        # Verify stopped
        assert not backend.is_running()

    def test_backend_thread_double_start(self, test_config):
        """Test calling start() twice doesn't create multiple threads."""
        backend = BackendThread(test_config)
        backend.running = True  # Simulate already running

        backend.start()  # Should log warning and return

        # Should not have started new thread
        assert backend.thread is None

    def test_backend_thread_stop_when_not_running(self, test_config):
        """Test calling stop() when backend not running."""
        backend = BackendThread(test_config)

        # Should not crash
        backend.stop()
        assert not backend.is_running()

    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    def test_backend_thread_camera_open_failure(
        self,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_flask_app
    ):
        """Test backend handles camera open failure gracefully."""
        # Camera fails to open
        mock_camera = Mock()
        mock_camera.open.return_value = False
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app

        backend = BackendThread(test_config)
        backend.start()

        # Wait for thread to process
        time.sleep(1)

        # Backend should stop gracefully
        assert not backend.is_running()

    @patch('app.standalone.camera_windows.WindowsCamera', side_effect=ImportError("Camera not available"))
    @patch('app.create_app')
    def test_backend_thread_camera_import_failure(
        self,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_flask_app
    ):
        """Test backend handles WindowsCamera import failure."""
        mock_create_app.return_value = mock_flask_app

        backend = BackendThread(test_config)
        backend.start()

        # Wait for thread to process
        time.sleep(1)

        # Backend should stop gracefully (camera not available)
        assert not backend.is_running()


class TestBackendThreadStatus:
    """Test BackendThread status methods."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_get_status_when_running(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test get_status() when backend running."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)

        status = backend.get_status()

        assert status['running'] is True
        assert 'pipeline_active' in status
        assert 'camera_connected' in status
        assert 'monitoring_active' in status

        backend.stop()

    def test_get_status_when_not_running(self, test_config):
        """Test get_status() when backend not running."""
        backend = BackendThread(test_config)

        status = backend.get_status()

        assert status['running'] is False
        assert status['pipeline_active'] is False
        assert status['camera_connected'] is False
        assert status['monitoring_active'] is False

    def test_is_running_returns_false_when_stopped(self, test_config):
        """Test is_running() returns False when stopped."""
        backend = BackendThread(test_config)
        assert not backend.is_running()


class TestBackendThreadControls:
    """Test pause/resume controls."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_pause_monitoring(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test pause_monitoring() calls alert manager."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)

        # Pause monitoring
        backend.pause_monitoring()

        # Verify alert manager called
        mock_cv_pipeline.alert_manager.pause_monitoring.assert_called_once()

        backend.stop()

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_resume_monitoring(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test resume_monitoring() calls alert manager."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)

        # Resume monitoring
        backend.resume_monitoring()

        # Verify alert manager called
        mock_cv_pipeline.alert_manager.resume_monitoring.assert_called_once()

        backend.stop()

    def test_pause_monitoring_no_pipeline(self, test_config):
        """Test pause_monitoring() when no pipeline (doesn't crash)."""
        backend = BackendThread(test_config)
        backend.pause_monitoring()  # Should not crash

    def test_resume_monitoring_no_pipeline(self, test_config):
        """Test resume_monitoring() when no pipeline (doesn't crash)."""
        backend = BackendThread(test_config)
        backend.resume_monitoring()  # Should not crash


class TestBackendThreadAnalytics:
    """Test analytics methods."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_get_today_stats_success(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test get_today_stats() returns data."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        # Mock analytics function
        with patch('app.data.analytics.PostureAnalytics.calculate_daily_stats') as mock_stats:
            mock_stats.return_value = {
                'good_duration_seconds': 7200,
                'bad_duration_seconds': 1800,
                'posture_score': 85.5
            }

            backend = BackendThread(test_config)
            backend.start()
            time.sleep(1)

            stats = backend.get_today_stats()

            # Should return stats
            assert stats is not None
            assert 'posture_score' in stats

            backend.stop()

    def test_get_today_stats_no_app(self, test_config):
        """Test get_today_stats() when no Flask app."""
        backend = BackendThread(test_config)
        stats = backend.get_today_stats()
        assert stats is None

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_get_history_success(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test get_history() returns data."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        # Mock analytics function
        with patch('app.data.analytics.PostureAnalytics.get_7_day_history') as mock_history:
            mock_history.return_value = [
                {'date': '2026-01-01', 'posture_score': 80},
                {'date': '2026-01-02', 'posture_score': 85}
            ]

            backend = BackendThread(test_config)
            backend.start()
            time.sleep(1)

            history = backend.get_history(days=7)

            # Should return history
            assert history is not None
            assert len(history) == 2

            backend.stop()

    def test_get_history_no_app(self, test_config):
        """Test get_history() when no Flask app."""
        backend = BackendThread(test_config)
        history = backend.get_history()
        assert history is None


class TestSingletonPattern:
    """Test global backend singleton functions."""

    def test_get_backend_returns_none_initially(self):
        """Test get_backend() returns None when not started."""
        # Reset global instance
        import app.standalone.backend_thread as bt
        bt._backend_instance = None

        backend = get_backend()
        assert backend is None

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_start_backend_creates_singleton(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test start_backend() creates singleton instance."""
        import app.standalone.backend_thread as bt
        bt._backend_instance = None

        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend1 = start_backend(test_config)
        backend2 = start_backend(test_config)

        # Should return same instance
        assert backend1 is backend2
        assert backend1 is not None

        stop_backend()

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_stop_backend_clears_singleton(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test stop_backend() clears global instance."""
        import app.standalone.backend_thread as bt
        bt._backend_instance = None

        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = start_backend(test_config)
        assert backend is not None

        stop_backend()

        # Global instance should be None
        assert get_backend() is None

    def test_stop_backend_when_not_started(self):
        """Test stop_backend() when backend not started."""
        import app.standalone.backend_thread as bt
        bt._backend_instance = None

        # Should not crash
        stop_backend()


class TestErrorHandling:
    """Test comprehensive error handling."""

    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    def test_backend_handles_flask_app_creation_failure(
        self,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata
    ):
        """Test backend handles Flask app creation failure."""
        # create_app raises exception
        mock_create_app.side_effect = Exception("Flask creation failed")

        backend = BackendThread(test_config)
        backend.start()

        # Wait for thread to process error
        time.sleep(1)

        # Should stop gracefully
        assert not backend.is_running()

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_backend_handles_cv_pipeline_failure(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_flask_app
    ):
        """Test backend handles CV pipeline initialization failure."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app

        # CVPipeline raises exception
        mock_cvpipeline_class.side_effect = Exception("CV pipeline failed")

        backend = BackendThread(test_config)
        backend.start()

        # Wait for thread to process error
        time.sleep(1)

        # Should stop gracefully
        assert not backend.is_running()

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_cleanup_called_on_exception(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test _cleanup() called even when exception occurs."""
        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        # Make pipeline.start() raise exception
        mock_cv_pipeline.start.side_effect = Exception("Pipeline start failed")

        backend = BackendThread(test_config)
        backend.start()

        # Wait for thread to process
        time.sleep(1)

        # Cleanup should have been called
        assert not backend.is_running()
        # Pipeline stop should have been called in cleanup
        mock_cv_pipeline.stop.assert_called()


class TestThreadSafety:
    """Test thread-safe operations."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.create_app')
    @patch('app.cv.pipeline.CVPipeline')
    def test_concurrent_singleton_access(
        self,
        mock_cvpipeline_class,
        mock_create_app,
        mock_camera_class,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline,
        mock_flask_app
    ):
        """Test concurrent access to singleton is thread-safe."""
        import app.standalone.backend_thread as bt
        bt._backend_instance = None

        mock_camera_class.return_value = mock_camera
        mock_create_app.return_value = mock_flask_app
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        # Start multiple threads trying to create backend
        backends = []

        def start_worker():
            backends.append(start_backend(test_config))

        threads = [threading.Thread(target=start_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should get same instance
        assert all(b is backends[0] for b in backends)
        assert len(set(id(b) for b in backends)) == 1

        stop_backend()
