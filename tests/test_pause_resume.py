"""Tests for pause/resume monitoring controls - Story 3.4."""

import pytest
from app.extensions import socketio


@pytest.fixture
def socketio_client(app):
    """Create test SocketIO client with mocked cv_pipeline from conftest."""
    return socketio.test_client(app)


class TestPauseMonitoring:
    """Test pause_monitoring event handler."""

    def test_pause_monitoring_event_exists(self, socketio_client, mock_cv_pipeline_global):
        """Test that pause_monitoring event handler is registered."""
        # Emit pause_monitoring event
        socketio_client.emit('pause_monitoring')

        # Should receive monitoring_status response
        received = socketio_client.get_received()
        assert len(received) > 0

        # Find monitoring_status event
        monitoring_events = [r for r in received if r['name'] == 'monitoring_status']
        assert len(monitoring_events) > 0, "Expected monitoring_status event after pause"

    def test_pause_calls_alert_manager(self, socketio_client, mock_cv_pipeline_global):
        """Test that pause_monitoring calls AlertManager.pause_monitoring()."""
        # Reset mock call count
        mock_cv_pipeline_global.alert_manager.pause_monitoring.reset_mock()

        # Emit pause event
        socketio_client.emit('pause_monitoring')

        # Verify pause_monitoring was called
        mock_cv_pipeline_global.alert_manager.pause_monitoring.assert_called_once()

    def test_pause_broadcasts_status(self, socketio_client, mock_cv_pipeline_global):
        """Test that pause_monitoring broadcasts monitoring_status to all clients."""
        # Configure mock to return paused status
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.return_value = {
            'monitoring_active': False,
            'threshold_seconds': 600,
            'cooldown_seconds': 300
        }

        # Reset mock call count
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.reset_mock()

        # Emit pause event
        socketio_client.emit('pause_monitoring')

        # Verify get_monitoring_status was called
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.assert_called_once()

        # Verify monitoring_status event received
        received = socketio_client.get_received()
        monitoring_events = [r for r in received if r['name'] == 'monitoring_status']

        assert len(monitoring_events) > 0
        status_data = monitoring_events[0]['args'][0]
        assert status_data['monitoring_active'] is False

    def test_pause_handles_missing_cv_pipeline(self, socketio_client, monkeypatch):
        """Test pause_monitoring handles cv_pipeline=None gracefully."""
        # Import app module to patch
        import app

        # Temporarily set cv_pipeline to None
        original_pipeline = app.cv_pipeline
        app.cv_pipeline = None

        # Emit pause event
        socketio_client.emit('pause_monitoring')

        # Should receive error event
        received = socketio_client.get_received()
        error_events = [r for r in received if r['name'] == 'error']

        assert len(error_events) > 0
        error_data = error_events[0]['args'][0]
        assert 'unavailable' in error_data['message'].lower() or \
               'not started' in error_data['message'].lower()

        # Restore original pipeline
        app.cv_pipeline = original_pipeline


class TestResumeMonitoring:
    """Test resume_monitoring event handler."""

    def test_resume_monitoring_event_exists(self, socketio_client, mock_cv_pipeline_global):
        """Test that resume_monitoring event handler is registered."""
        # Emit resume_monitoring event
        socketio_client.emit('resume_monitoring')

        # Should receive monitoring_status response
        received = socketio_client.get_received()
        assert len(received) > 0

        # Find monitoring_status event
        monitoring_events = [r for r in received if r['name'] == 'monitoring_status']
        assert len(monitoring_events) > 0, "Expected monitoring_status event after resume"

    def test_resume_calls_alert_manager(self, socketio_client, mock_cv_pipeline_global):
        """Test that resume_monitoring calls AlertManager.resume_monitoring()."""
        # Reset mock call count
        mock_cv_pipeline_global.alert_manager.resume_monitoring.reset_mock()

        # Emit resume event
        socketio_client.emit('resume_monitoring')

        # Verify resume_monitoring was called
        mock_cv_pipeline_global.alert_manager.resume_monitoring.assert_called_once()

    def test_resume_broadcasts_status(self, socketio_client, mock_cv_pipeline_global):
        """Test that resume_monitoring broadcasts monitoring_status to all clients."""
        # Configure mock to return active status
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.return_value = {
            'monitoring_active': True,
            'threshold_seconds': 600,
            'cooldown_seconds': 300
        }

        # Reset mock call count
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.reset_mock()

        # Emit resume event
        socketio_client.emit('resume_monitoring')

        # Verify get_monitoring_status was called
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.assert_called_once()

        # Verify monitoring_status event received
        received = socketio_client.get_received()
        monitoring_events = [r for r in received if r['name'] == 'monitoring_status']

        assert len(monitoring_events) > 0
        status_data = monitoring_events[0]['args'][0]
        assert status_data['monitoring_active'] is True

    def test_resume_handles_missing_cv_pipeline(self, socketio_client, monkeypatch):
        """Test resume_monitoring handles cv_pipeline=None gracefully."""
        # Import app module to patch
        import app

        # Temporarily set cv_pipeline to None
        original_pipeline = app.cv_pipeline
        app.cv_pipeline = None

        # Emit resume event
        socketio_client.emit('resume_monitoring')

        # Should receive error event
        received = socketio_client.get_received()
        error_events = [r for r in received if r['name'] == 'error']

        assert len(error_events) > 0
        error_data = error_events[0]['args'][0]
        assert 'unavailable' in error_data['message'].lower() or \
               'not started' in error_data['message'].lower()

        # Restore original pipeline
        app.cv_pipeline = original_pipeline


class TestMonitoringStatusBroadcast:
    """Test monitoring_status event broadcast behavior."""

    def test_monitoring_status_includes_required_fields(
        self, socketio_client, mock_cv_pipeline_global
    ):
        """Test monitoring_status event includes all required fields."""
        # Emit pause event (triggers status broadcast)
        socketio_client.emit('pause_monitoring')

        # Get monitoring_status event
        received = socketio_client.get_received()
        monitoring_events = [r for r in received if r['name'] == 'monitoring_status']

        assert len(monitoring_events) > 0
        status_data = monitoring_events[0]['args'][0]

        # Verify required fields
        assert 'monitoring_active' in status_data
        assert 'threshold_seconds' in status_data
        assert 'cooldown_seconds' in status_data
        assert isinstance(status_data['monitoring_active'], bool)
        assert isinstance(status_data['threshold_seconds'], int)
        assert isinstance(status_data['cooldown_seconds'], int)
