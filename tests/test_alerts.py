"""
Unit tests for alert threshold tracking and state management.

Story 3.1: Alert Threshold Tracking and State Management
"""

import pytest
import time
from unittest.mock import patch, Mock
from app.alerts.manager import AlertManager


class TestAlertManager:
    """Test suite for alert threshold tracking and state machine."""

    @pytest.fixture
    def alert_manager(self, app_context):
        """Create AlertManager instance with Flask app context."""
        return AlertManager()

    def test_alert_manager_initialization(self, alert_manager):
        """Test AlertManager initializes with correct defaults."""
        assert alert_manager.alert_threshold == 600  # 10 minutes
        assert alert_manager.alert_cooldown == 300  # 5 minutes
        assert alert_manager.bad_posture_start_time is None
        assert alert_manager.last_alert_time is None
        assert alert_manager.monitoring_paused is False

    def test_bad_posture_duration_tracking(self, alert_manager):
        """Test bad posture duration is tracked correctly."""
        # First update: bad posture detected
        with patch('time.time', return_value=1000.0):
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert result['threshold_reached'] is False

        # Second update: 5 minutes elapsed (not yet threshold)
        with patch('time.time', return_value=1300.0):  # +300 seconds
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is False
            assert result['duration'] == 300
            assert result['threshold_reached'] is False

        # Third update: 10 minutes elapsed (threshold reached)
        with patch('time.time', return_value=1600.0):  # +600 seconds
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is True  # First alert
            assert result['duration'] == 600
            assert result['threshold_reached'] is True

    def test_alert_cooldown_prevents_spam(self, alert_manager):
        """Test alert cooldown prevents repeated alerts."""
        # Trigger first alert
        with patch('time.time', return_value=1000.0):
            alert_manager.process_posture_update('bad', user_present=True)

        with patch('time.time', return_value=1600.0):  # +600s (threshold)
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is True  # First alert

        # Cooldown period: 2 minutes later (still in cooldown)
        with patch('time.time', return_value=1720.0):  # +120s
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is False  # Cooldown active
            assert result['threshold_reached'] is True

        # Cooldown expired: 5 minutes later
        with patch('time.time', return_value=1900.0):  # +300s (cooldown expired)
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is True  # Cooldown expired, send reminder
            assert result['duration'] == 900  # Total bad posture duration

    def test_good_posture_resets_tracking(self, alert_manager):
        """Test good posture resets bad posture tracking."""
        # Start bad posture tracking
        with patch('time.time', return_value=1000.0):
            alert_manager.process_posture_update('bad', user_present=True)

        # Good posture detected
        with patch('time.time', return_value=1300.0):
            result = alert_manager.process_posture_update('good', user_present=True)
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert alert_manager.bad_posture_start_time is None
            assert alert_manager.last_alert_time is None

    def test_user_absent_resets_tracking(self, alert_manager):
        """Test user absence resets bad posture tracking."""
        # Start bad posture tracking
        with patch('time.time', return_value=1000.0):
            alert_manager.process_posture_update('bad', user_present=True)

        # User leaves desk
        result = alert_manager.process_posture_update('bad', user_present=False)
        assert result['should_alert'] is False
        assert result['duration'] == 0
        assert alert_manager.bad_posture_start_time is None

    def test_none_posture_state_resets_tracking(self, alert_manager):
        """Test None posture state (camera disconnected) resets tracking."""
        # Start bad posture tracking
        with patch('time.time', return_value=1000.0):
            alert_manager.process_posture_update('bad', user_present=True)

        # Camera disconnected (posture_state=None)
        result = alert_manager.process_posture_update(None, user_present=False)
        assert result['should_alert'] is False
        assert result['duration'] == 0
        assert alert_manager.bad_posture_start_time is None

    def test_camera_disconnect_resets_tracking(self, alert_manager):
        """Test camera disconnect (Story 2.7 integration) resets alert tracking."""
        # Start bad posture tracking
        with patch('time.time', return_value=1000.0):
            alert_manager.process_posture_update('bad', user_present=True)
            assert alert_manager.bad_posture_start_time is not None

        # Camera disconnects - represented by posture_state=None, user_present=False
        # (Simulates: camera_state='disconnected' → detector returns None landmarks)
        result = alert_manager.process_posture_update(None, user_present=False)

        assert result['should_alert'] is False
        assert result['duration'] == 0
        assert result['threshold_reached'] is False
        assert alert_manager.bad_posture_start_time is None

        # Verify tracking stays reset until camera reconnects
        with patch('time.time', return_value=1300.0):
            result = alert_manager.process_posture_update(None, user_present=False)
            assert alert_manager.bad_posture_start_time is None

    def test_monitoring_paused_stops_tracking(self, alert_manager):
        """Test pause monitoring stops all tracking (FR11)."""
        # Start bad posture tracking
        with patch('time.time', return_value=1000.0):
            alert_manager.process_posture_update('bad', user_present=True)

        # Pause monitoring
        alert_manager.pause_monitoring()

        # Tracking should stop even with bad posture
        with patch('time.time', return_value=1600.0):
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert alert_manager.monitoring_paused is True

    def test_resume_monitoring_restarts_tracking(self, alert_manager):
        """Test resume monitoring allows tracking to restart (FR12)."""
        # Pause monitoring
        alert_manager.pause_monitoring()
        assert alert_manager.monitoring_paused is True

        # Resume monitoring
        alert_manager.resume_monitoring()
        assert alert_manager.monitoring_paused is False

        # Tracking should work again
        with patch('time.time', return_value=1000.0):
            result = alert_manager.process_posture_update('bad', user_present=True)
            assert alert_manager.bad_posture_start_time is not None

    def test_get_monitoring_status(self, alert_manager):
        """Test get_monitoring_status returns correct state (FR13)."""
        status = alert_manager.get_monitoring_status()
        assert status['monitoring_active'] is True
        assert status['threshold_seconds'] == 600
        assert status['cooldown_seconds'] == 300

        alert_manager.pause_monitoring()
        status = alert_manager.get_monitoring_status()
        assert status['monitoring_active'] is False


@pytest.fixture
def app_context():
    """Create Flask app context for testing."""
    from app import create_app
    app = create_app()
    with app.app_context():
        yield app
