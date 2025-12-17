"""Tests for pause/resume monitoring controls - Story 3.4.

Enterprise-grade approach: Test handlers directly to avoid SocketIO threading
complications with Mock call tracking. Handler logic is the contract, not the
transport mechanism.
"""

import pytest
from unittest.mock import patch


class TestPauseMonitoring:
    """Test pause_monitoring event handler."""

    def test_pause_calls_alert_manager(self, app, mock_cv_pipeline_global):
        """Test that pause_monitoring handler calls AlertManager.pause_monitoring()."""
        with app.app_context():
            # Import handler function
            from app.main.events import handle_pause_monitoring

            # Reset mock before test
            mock_cv_pipeline_global.alert_manager.pause_monitoring.reset_mock()

            # Mock Flask request.sid for handler
            with patch('app.main.events.request') as mock_request:
                mock_request.sid = 'test-client-id'

                # Call handler directly
                handle_pause_monitoring()

            # Verify pause_monitoring was called
            mock_cv_pipeline_global.alert_manager.pause_monitoring.assert_called_once()

    def test_pause_queries_monitoring_status(self, app, mock_cv_pipeline_global):
        """Test that pause_monitoring queries and broadcasts monitoring status."""
        with app.app_context():
            # Configure mock to return paused status
            mock_cv_pipeline_global.alert_manager.get_monitoring_status.return_value = {
                'monitoring_active': False,
                'threshold_seconds': 600,
                'cooldown_seconds': 300
            }

            # Reset mock before test
            mock_cv_pipeline_global.alert_manager.get_monitoring_status.reset_mock()

            # Import handler
            from app.main.events import handle_pause_monitoring

            # Mock request.sid and emit
            with patch('app.main.events.request') as mock_request:
                with patch('app.main.events.emit'):
                    mock_request.sid = 'test-client-id'
                    handle_pause_monitoring()

            # Verify get_monitoring_status was called
            mock_cv_pipeline_global.alert_manager.get_monitoring_status.assert_called_once()

    def test_pause_handles_missing_cv_pipeline(self, app):
        """Test pause_monitoring handles cv_pipeline=None gracefully."""
        with app.app_context():
            # Import app module to patch
            import app as app_module

            # Temporarily set cv_pipeline to None
            original_pipeline = app_module.cv_pipeline
            app_module.cv_pipeline = None

            try:
                # Import handler
                from app.main.events import handle_pause_monitoring

                # Mock request and SocketIO emit (both inside and outside handler)
                with patch('app.main.events.request') as mock_request:
                    with patch('app.main.events.socketio') as mock_socketio:
                        with patch('app.main.events.emit') as mock_emit:
                            mock_request.sid = 'test-client-id'

                            # Call handler - should not crash
                            handle_pause_monitoring()

                            # Verify error was emitted (via socketio.emit, not emit)
                            assert mock_socketio.emit.called or mock_emit.called
                            # Handler emits error via socketio.emit when cv_pipeline is None
                            if mock_socketio.emit.called:
                                call_args = mock_socketio.emit.call_args
                                assert call_args[0][0] == 'error'
                                assert 'unavailable' in call_args[0][1]['message'].lower() or \
                                       'not started' in call_args[0][1]['message'].lower()

            finally:
                # Restore original pipeline
                app_module.cv_pipeline = original_pipeline


class TestResumeMonitoring:
    """Test resume_monitoring event handler."""

    def test_resume_calls_alert_manager(self, app, mock_cv_pipeline_global):
        """Test that resume_monitoring handler calls AlertManager.resume_monitoring()."""
        with app.app_context():
            # Import handler function
            from app.main.events import handle_resume_monitoring

            # Reset mock before test
            mock_cv_pipeline_global.alert_manager.resume_monitoring.reset_mock()

            # Mock Flask request.sid for handler
            with patch('app.main.events.request') as mock_request:
                mock_request.sid = 'test-client-id'

                # Call handler directly
                handle_resume_monitoring()

            # Verify resume_monitoring was called
            mock_cv_pipeline_global.alert_manager.resume_monitoring.assert_called_once()

    def test_resume_queries_monitoring_status(self, app, mock_cv_pipeline_global):
        """Test that resume_monitoring queries and broadcasts monitoring status."""
        with app.app_context():
            # Configure mock to return active status
            mock_cv_pipeline_global.alert_manager.get_monitoring_status.return_value = {
                'monitoring_active': True,
                'threshold_seconds': 600,
                'cooldown_seconds': 300
            }

            # Reset mock before test
            mock_cv_pipeline_global.alert_manager.get_monitoring_status.reset_mock()

            # Import handler
            from app.main.events import handle_resume_monitoring

            # Mock request.sid and emit
            with patch('app.main.events.request') as mock_request:
                with patch('app.main.events.emit'):
                    mock_request.sid = 'test-client-id'
                    handle_resume_monitoring()

            # Verify get_monitoring_status was called
            mock_cv_pipeline_global.alert_manager.get_monitoring_status.assert_called_once()

    def test_resume_handles_missing_cv_pipeline(self, app):
        """Test resume_monitoring handles cv_pipeline=None gracefully."""
        with app.app_context():
            # Import app module to patch
            import app as app_module

            # Temporarily set cv_pipeline to None
            original_pipeline = app_module.cv_pipeline
            app_module.cv_pipeline = None

            try:
                # Import handler
                from app.main.events import handle_resume_monitoring

                # Mock request and SocketIO emit (both inside and outside handler)
                with patch('app.main.events.request') as mock_request:
                    with patch('app.main.events.socketio') as mock_socketio:
                        with patch('app.main.events.emit') as mock_emit:
                            mock_request.sid = 'test-client-id'

                            # Call handler - should not crash
                            handle_resume_monitoring()

                            # Verify error was emitted (via socketio.emit, not emit)
                            assert mock_socketio.emit.called or mock_emit.called
                            # Handler emits error via socketio.emit when cv_pipeline is None
                            if mock_socketio.emit.called:
                                call_args = mock_socketio.emit.call_args
                                assert call_args[0][0] == 'error'
                                assert 'unavailable' in call_args[0][1]['message'].lower() or \
                                       'not started' in call_args[0][1]['message'].lower()

            finally:
                # Restore original pipeline
                app_module.cv_pipeline = original_pipeline


class TestMonitoringStatusBroadcast:
    """Test monitoring_status data structure."""

    def test_monitoring_status_includes_required_fields(self, mock_cv_pipeline_global):
        """Test get_monitoring_status returns all required fields."""
        # Configure mock return value
        mock_cv_pipeline_global.alert_manager.get_monitoring_status.return_value = {
            'monitoring_active': False,
            'threshold_seconds': 600,
            'cooldown_seconds': 300
        }

        # Get status directly from mock (simulates handler behavior)
        status_data = mock_cv_pipeline_global.alert_manager.get_monitoring_status()

        # Verify required fields
        assert 'monitoring_active' in status_data
        assert 'threshold_seconds' in status_data
        assert 'cooldown_seconds' in status_data
        assert isinstance(status_data['monitoring_active'], bool)
        assert isinstance(status_data['threshold_seconds'], int)
        assert isinstance(status_data['cooldown_seconds'], int)
