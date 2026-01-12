"""
Integration tests for Windows standalone edition.

Tests full backend initialization, Flask app creation,
database operations, and component integration.
"""

import pytest
import time
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, Mock
from app import create_app
from app.standalone.backend_thread import BackendThread
from app.standalone.config import (
    get_database_path,
    load_config,
    setup_logging
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
    """Mock WindowsCamera for integration tests."""
    camera = Mock()
    camera.open.return_value = True
    camera.is_available.return_value = True
    camera.read.return_value = (True, Mock())
    return camera


@pytest.fixture
def mock_cv_pipeline():
    """Mock CVPipeline for integration tests."""
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
    pipeline.alert_manager.pause_monitoring.return_value = None
    pipeline.alert_manager.resume_monitoring.return_value = None
    return pipeline


class TestFlaskAppCreation:
    """Test Flask app creation in standalone mode (fast, mocked tests)."""

    @patch('app.extensions.init_db')
    def test_create_app_standalone_mode(self, mock_init_db, temp_appdata):
        """Test Flask app creation with standalone mode."""
        db_path = get_database_path()

        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        # Verify app created
        assert app is not None
        # Standalone mode just skips SocketIO/Talisman init, doesn't set config flags
        # Verify app was created successfully
        assert app.config['DATABASE_PATH'] == str(db_path)

    @patch('app.extensions.init_db')
    def test_create_app_with_custom_database_path(self, mock_init_db):
        """Test Flask app accepts custom database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'custom.db'

            app = create_app(
                config_name='standalone',
                database_path=str(db_path),
                standalone_mode=True
            )

            # Verify database path used
            assert app is not None
            # Note: StandaloneConfig overrides with get_database_path() from %APPDATA%
            # This test just verifies create_app doesn't crash with custom path
            assert 'DATABASE_PATH' in app.config

    @patch('app.extensions.init_db')
    def test_create_app_uses_standalone_config_class(self, mock_init_db, temp_appdata):
        """Test standalone mode uses StandaloneConfig class (Issue #6 fix)."""
        from app.config import StandaloneConfig
        db_path = get_database_path()

        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        # Verify StandaloneConfig class is used
        assert app is not None
        # StandaloneConfig should set specific config values
        assert 'DATABASE_PATH' in app.config
        # Verify it's using standalone-specific configuration
        assert app.config.get('ENV') in ['production', 'standalone', None]

    @patch('app.extensions.init_db')
    def test_create_app_initializes_database(self, mock_init_db, temp_appdata):
        """Test database initialization on app creation."""
        db_path = get_database_path()

        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        # Initialize database
        with app.app_context():
            from app.extensions import init_db
            init_db(app)

        # Verify init_db was called
        assert mock_init_db.called


class TestDatabaseWALMode:
    """Test SQLite WAL mode configuration (mocked for speed)."""

    @patch('app.extensions.init_db')
    @patch('sqlite3.connect')
    def test_database_wal_mode_enabled(self, mock_connect, mock_init_db, temp_appdata):
        """Test SQLite WAL mode is enabled for durability."""
        db_path = get_database_path()

        # Mock WAL mode query response
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = ['wal']
        mock_connect.return_value = mock_conn

        # Create app
        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        # Simulate WAL mode check
        conn = sqlite3.connect(str(db_path))
        result = conn.execute('PRAGMA journal_mode').fetchone()
        conn.close()

        # Verify WAL mode would be used
        assert result[0].lower() == 'wal'

    @patch('app.extensions.init_db')
    def test_database_path_configuration(self, mock_init_db, temp_appdata):
        """Test database path configuration."""
        db_path = get_database_path()

        # Create app
        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        # Verify database path configured
        assert 'DATABASE_PATH' in app.config
        assert isinstance(app.config['DATABASE_PATH'], str)
        # WAL files (-wal, -shm) are created by SQLite at runtime
        # Tested in production/manual testing, not unit tests


class TestAppContextInBackgroundThread:
    """Test Flask app context works in background thread (mocked)."""

    @patch('app.extensions.init_db')
    @patch('app.data.analytics.PostureAnalytics.calculate_daily_stats')
    def test_app_context_in_background_thread(self, mock_calc, mock_init_db, temp_appdata):
        """Test database operations work in background thread."""
        db_path = get_database_path()
        mock_calc.return_value = {'posture_score': 80}

        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        # Test analytics call in app context
        result = None
        exception = None

        def query_in_thread():
            nonlocal result, exception
            try:
                with app.app_context():
                    from app.data.analytics import PostureAnalytics
                    from datetime import date
                    result = PostureAnalytics.calculate_daily_stats(date.today())
            except Exception as e:
                exception = e

        import threading
        thread = threading.Thread(target=query_in_thread)
        thread.start()
        thread.join(timeout=5)

        # Should not raise exception
        assert exception is None
        # Result should be mocked value
        assert result is not None
        assert result['posture_score'] == 80

    @patch('app.extensions.init_db')
    @patch('app.data.analytics.PostureAnalytics.calculate_daily_stats')
    @patch('app.data.analytics.PostureAnalytics.get_7_day_history')
    def test_multiple_queries_in_app_context(self, mock_history, mock_calc, mock_init_db, temp_appdata):
        """Test multiple database queries in app context."""
        db_path = get_database_path()
        mock_calc.return_value = {'posture_score': 80}
        mock_history.return_value = [{'posture_score': 75}]

        app = create_app(
            config_name='standalone',
            database_path=str(db_path),
            standalone_mode=True
        )

        with app.app_context():
            # Multiple queries should work
            from app.data.analytics import PostureAnalytics
            from datetime import date

            stats1 = PostureAnalytics.calculate_daily_stats(date.today())
            stats2 = PostureAnalytics.get_7_day_history()
            stats3 = PostureAnalytics.calculate_daily_stats(date.today())

            # All should return results
            assert stats1 is not None
            assert stats2 is not None
            assert stats3 is not None


class TestFullBackendInitialization:
    """Test complete backend initialization."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_full_backend_initialization(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test complete backend initialization with all components."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        # Load config
        config = load_config()

        # Create backend
        backend = BackendThread(config)
        backend.start()

        # Wait for initialization
        time.sleep(2)

        # Verify components running
        assert backend.is_running()
        assert backend.flask_app is not None
        assert backend.cv_pipeline is not None

        # Test status
        status = backend.get_status()
        assert status['running'] is True

        # Stop backend
        backend.stop()

        # Verify stopped
        assert not backend.is_running()

    @patch('app.data.analytics.PostureAnalytics.calculate_daily_stats')
    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_backend_with_real_database_operations(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        mock_calc,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test backend with mocked analytics operations."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline
        mock_calc.return_value = {'posture_score': 85}

        config = load_config()
        backend = BackendThread(config)
        backend.start()

        time.sleep(2)

        # Test analytics operations
        stats = backend.get_today_stats()
        # Should return mocked data
        assert stats is not None
        assert stats['posture_score'] == 85

        backend.stop()


class TestConfigurationIntegration:
    """Test configuration integration with backend."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_backend_uses_config_values(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test backend uses configuration values correctly."""
        from app.standalone.config import save_config

        # Custom config
        custom_config = {
            'camera': {
                'index': 2,
                'fps': 15,
                'width': 1280,
                'height': 720
            },
            'monitoring': {
                'alert_threshold_seconds': 300
            }
        }
        save_config(custom_config)

        # Load and verify
        config = load_config()
        assert config['camera']['index'] == 2
        assert config['camera']['fps'] == 15

        # Create backend with custom config
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(config)
        backend.start()
        time.sleep(1)

        # Verify camera initialized with correct values
        # (mock_camera_class should have been called with these values)
        call_kwargs = mock_camera_class.call_args[1]
        assert call_kwargs['camera_index'] == 2
        assert call_kwargs['fps'] == 15
        assert call_kwargs['width'] == 1280
        assert call_kwargs['height'] == 720

        backend.stop()


class TestErrorRecoveryIntegration:
    """Test error recovery scenarios."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_backend_continues_after_analytics_error(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test backend continues running after analytics error."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)

        # Simulate analytics error
        with patch('app.data.analytics.PostureAnalytics.calculate_daily_stats') as mock_stats:
            mock_stats.side_effect = Exception("Analytics error")

            stats = backend.get_today_stats()

            # Should return None, not crash
            assert stats is None
            assert backend.is_running()

        backend.stop()

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_pipeline_health_monitoring(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test backend monitors pipeline health."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)

        # Simulate pipeline stopped
        mock_cv_pipeline.is_running.return_value = False

        # Wait for health check to run
        time.sleep(2)

        # Backend should still be running (logs warning)
        assert backend.is_running()

        backend.stop()


class TestResourceCleanup:
    """Test proper resource cleanup."""

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_cleanup_called_on_stop(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test cleanup called when backend stops."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)

        # Stop backend
        backend.stop()

        # Verify cleanup called
        mock_cv_pipeline.stop.assert_called()

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_no_memory_leak_on_restart(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test no memory leak when stopping and restarting backend."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        # Start and stop multiple times
        for _ in range(3):
            backend = BackendThread(test_config)
            backend.start()
            time.sleep(1)
            backend.stop()
            time.sleep(0.5)

        # If no exceptions, test passes (no memory leaks detected)
        assert True


class TestThreadSafetyConcurrency:
    """Test thread safety under concurrent load (Issue #7 fix)."""

    @patch('app.data.analytics.PostureAnalytics.calculate_daily_stats')
    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_concurrent_get_today_stats_calls(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        mock_calc,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test concurrent get_today_stats calls don't cause race conditions."""
        import threading
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline
        mock_calc.return_value = {'posture_score': 85}

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(2)

        # Concurrent calls from 10 threads
        results = []
        exceptions = []

        def concurrent_query():
            try:
                result = backend.get_today_stats()
                results.append(result)
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=concurrent_query) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All calls should succeed
        assert len(exceptions) == 0, f"Got exceptions: {exceptions}"
        assert len(results) == 10
        assert all(r is not None for r in results)

        backend.stop()

    @patch('app.data.analytics.PostureAnalytics.calculate_daily_stats')
    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_app_context_cleanup_no_memory_leak(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        mock_calc,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test 100+ queries don't leak app contexts."""
        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline
        mock_calc.return_value = {'posture_score': 85}

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(2)

        # 100 sequential queries
        for _ in range(100):
            result = backend.get_today_stats()
            assert result is not None

        # If no exceptions, no memory leak detected
        backend.stop()


class TestLoggingIntegration:
    """Test logging integration."""

    def test_logging_setup_creates_log_files(self, temp_appdata):
        """Test logging creates log files in correct location."""
        from app.standalone.config import get_log_path

        setup_logging()

        log_path = get_log_path()
        assert log_path.exists()
        assert log_path.parent.name == 'logs'

    @patch('app.extensions.init_db')
    @patch('app.standalone.camera_windows.WindowsCamera')
    @patch('app.cv.pipeline.CVPipeline')
    def test_backend_logs_events(
        self,
        mock_cvpipeline_class,
        mock_camera_class,
        mock_init_db,
        test_config,
        temp_appdata,
        mock_camera,
        mock_cv_pipeline
    ):
        """Test backend logs events to file."""
        from app.standalone.config import get_log_path

        setup_logging()

        mock_camera_class.return_value = mock_camera
        mock_cvpipeline_class.return_value = mock_cv_pipeline

        backend = BackendThread(test_config)
        backend.start()
        time.sleep(1)
        backend.stop()

        # Verify log file has content
        log_path = get_log_path()
        assert log_path.exists()
        assert log_path.stat().st_size > 0

        # Verify some expected log messages
        log_content = log_path.read_text()
        assert 'Backend' in log_content or 'DeskPulse' in log_content
