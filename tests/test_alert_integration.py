"""Integration tests for alert response loop - Story 3.6

This module tests the complete alert response loop integration across
Stories 3.1-3.5, validating that all Epic 3 components work together:
- Alert threshold tracking and state management (Story 3.1)
- Desktop notifications (Story 3.2)
- Browser notifications via SocketIO (Story 3.3)
- Pause/resume monitoring controls (Story 3.4)
- Posture correction confirmation feedback (Story 3.5)

Note: Uses mock_cv_pipeline_global fixture from conftest.py automatically.
No additional CV pipeline mocking needed - focus on AlertManager state and
SocketIO emissions.
"""

import pytest
import time
from unittest.mock import patch, Mock, MagicMock
from app.alerts.manager import AlertManager


class TestAlertResponseLoopIntegration:
    """Integration tests for complete alert cycle (Stories 3.1-3.5)."""

    @pytest.fixture
    def manager(self, app):
        """Create AlertManager instance with test config."""
        with app.app_context():
            return AlertManager()

    def test_basic_alert_flow_happy_path(self, manager):
        """Test complete alert cycle: good → bad → alert → correction (AC1).

        Validates:
        - Good posture: no alerts, duration=0
        - Bad posture detected: tracking starts
        - 10 minute threshold: should_alert=True, threshold_reached=True
        - Correction to good: posture_corrected=True, state reset
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Step 1: User sits in good posture
            mock_time.return_value = 1000.0
            result = manager.process_posture_update('good', True)
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert result['threshold_reached'] is False
            assert manager.bad_posture_start_time is None

            # Step 2: User slouches (bad posture detected)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False
            assert result['duration'] == 0  # Just started
            assert result['threshold_reached'] is False
            assert manager.bad_posture_start_time is not None

            # Step 3: 10 minutes elapsed (threshold reached)
            mock_time.return_value = 1600.0  # +600s threshold
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True  # Alert triggered
            assert result['duration'] == 600
            assert result['threshold_reached'] is True
            assert manager.last_alert_time is not None

            # Step 4: User corrects posture (back to good)
            mock_time.return_value = 1650.0  # +50s after alert
            result = manager.process_posture_update('good', True)
            assert result.get('posture_corrected') is True  # Correction detected
            assert result.get('previous_duration') == 650  # Total bad duration
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert manager.bad_posture_start_time is None  # State reset
            assert manager.last_alert_time is None  # State reset

    def test_alert_cooldown_prevents_spam(self, manager):
        """Test alert cooldown prevents notification spam (AC2).

        Validates:
        - First alert at 10 minutes
        - Cooldown blocks alerts at 12 minutes (2 min after first)
        - Reminder alert at 15 minutes (5 min cooldown expired)
        - Duration tracking continues throughout
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start bad posture tracking
            mock_time.return_value = 1000.0
            result = manager.process_posture_update('bad', True)
            assert result['duration'] == 0

            # Step 1: Alert triggered at 10 minutes
            mock_time.return_value = 1600.0  # +600s (10 min)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True  # First alert
            assert result['duration'] == 600
            assert result['threshold_reached'] is True

            # Step 2: User remains in bad posture for 12 minutes (cooldown active)
            mock_time.return_value = 1720.0  # +120s (12 min total)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False  # Cooldown blocks alert
            assert result['duration'] == 720  # Duration continues tracking
            assert result['threshold_reached'] is True

            # Step 3: User remains in bad posture for 15 minutes (cooldown expired)
            mock_time.return_value = 1900.0  # +300s (15 min total)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True  # Cooldown expired, reminder sent
            assert result['duration'] == 900
            assert result['threshold_reached'] is True

            # Step 4: Verify cooldown prevents spam - 16 minutes (still in cooldown)
            mock_time.return_value = 1960.0  # +60s (16 min total)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False  # New cooldown active
            assert result['duration'] == 960

    def test_pause_monitoring_stops_alert_tracking(self, manager):
        """Test pause monitoring stops all tracking (AC3).

        Validates:
        - Pause resets bad_posture_start_time and last_alert_time
        - No alerts triggered while monitoring_paused=True
        - No duration tracking while paused
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start bad posture tracking
            mock_time.return_value = 1000.0
            result = manager.process_posture_update('bad', True)
            assert manager.bad_posture_start_time is not None

            # Step 1: User clicks "Pause Monitoring"
            manager.pause_monitoring()
            assert manager.monitoring_paused is True
            assert manager.bad_posture_start_time is None  # State reset
            assert manager.last_alert_time is None  # State reset

            # Step 2: User remains in bad posture while paused
            mock_time.return_value = 1600.0  # +600s (would trigger alert if not paused)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False  # No alert while paused
            assert result['duration'] == 0  # No duration tracking
            assert manager.bad_posture_start_time is None

            # Step 3: User clicks "Resume Monitoring"
            manager.resume_monitoring()
            assert manager.monitoring_paused is False

            # Step 4: New bad posture session tracked independently
            mock_time.return_value = 1700.0
            result = manager.process_posture_update('bad', True)
            assert manager.bad_posture_start_time is not None  # Fresh tracking
            assert result['duration'] == 0  # Fresh session (not carried over)

    def test_pause_prevents_false_confirmation(self, manager):
        """Test pause during alert prevents false confirmation after resume (AC3).

        Validates:
        - Bad posture → alert → pause → resume → good posture
        - NO posture_corrected event after resume (state was reset by pause)
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Bad posture + alert
            mock_time.return_value = 1000.0
            manager.process_posture_update('bad', True)

            mock_time.return_value = 1720.0  # +720s (12 min, alert triggered)
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True  # Alert triggered

            # User pauses monitoring
            manager.pause_monitoring()
            assert manager.bad_posture_start_time is None
            assert manager.last_alert_time is None

            # Resume and correct posture
            manager.resume_monitoring()
            mock_time.return_value = 1800.0
            result = manager.process_posture_update('good', True)

            # Should NOT detect correction (state was reset by pause)
            assert result.get('posture_corrected') is not True

    def test_user_absence_resets_tracking(self, manager):
        """Test user absence resets alert tracking (AC4).

        Validates:
        - User leaves desk (user_present=False) resets tracking
        - No alerts while user absent
        - Return to desk starts fresh tracking session
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start bad posture tracking
            mock_time.return_value = 1000.0
            result = manager.process_posture_update('bad', True)
            assert manager.bad_posture_start_time is not None

            # Step 1: User leaves desk (no pose detected)
            result = manager.process_posture_update('bad', user_present=False)
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert manager.bad_posture_start_time is None  # Tracking reset

            # Step 2: User remains absent
            mock_time.return_value = 1600.0  # +600s
            result = manager.process_posture_update('bad', user_present=False)
            assert result['should_alert'] is False
            assert manager.bad_posture_start_time is None

            # Step 3: User returns in bad posture
            mock_time.return_value = 1700.0
            result = manager.process_posture_update('bad', user_present=True)
            assert manager.bad_posture_start_time is not None  # Fresh tracking
            assert result['duration'] == 0  # Fresh session (doesn't count time away)

    def test_camera_disconnect_same_as_absence(self, manager):
        """Test camera disconnect (posture_state=None) same as user absence (AC4).

        Validates:
        - Camera disconnect represented by posture_state=None, user_present=False
        - State reset identical to user absence
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start bad posture tracking
            mock_time.return_value = 1000.0
            manager.process_posture_update('bad', True)
            assert manager.bad_posture_start_time is not None

            # Camera disconnects (posture_state=None, user_present=False)
            result = manager.process_posture_update(None, user_present=False)
            assert result['should_alert'] is False
            assert result['duration'] == 0
            assert result['threshold_reached'] is False
            assert manager.bad_posture_start_time is None  # State reset

            # Verify tracking stays reset until camera reconnects
            mock_time.return_value = 1300.0
            result = manager.process_posture_update(None, user_present=False)
            assert manager.bad_posture_start_time is None

    def test_correction_after_prolonged_bad_posture(self, manager):
        """Test correction after prolonged bad posture with multiple reminders (edge case).

        Validates:
        - 20 minutes bad posture with reminders at 10, 15, 20 minutes
        - Correction triggers confirmation with accurate previous_duration
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start bad posture
            mock_time.return_value = 1000.0
            manager.process_posture_update('bad', True)

            # First alert at 10 minutes
            mock_time.return_value = 1600.0  # +600s
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True

            # Reminder at 15 minutes
            mock_time.return_value = 1900.0  # +300s
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True

            # Reminder at 20 minutes
            mock_time.return_value = 2200.0  # +300s
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is True

            # User finally corrects posture
            mock_time.return_value = 2250.0  # +50s
            result = manager.process_posture_update('good', True)
            assert result.get('posture_corrected') is True
            assert result.get('previous_duration') == 1250  # Accurate total duration
            assert manager.bad_posture_start_time is None
            assert manager.last_alert_time is None

    def test_rapid_posture_changes_no_spam(self, manager):
        """Test rapid posture changes under threshold don't trigger alerts/confirmations (edge case).

        Validates:
        - Good → bad → good cycles under 10 min threshold
        - No alerts triggered
        - No confirmations sent (no alert was sent)
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Cycle 1: good → bad → good (5 minutes)
            mock_time.return_value = 1000.0
            result = manager.process_posture_update('good', True)
            assert result['should_alert'] is False

            mock_time.return_value = 1100.0  # +100s
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False
            assert result['duration'] == 0

            mock_time.return_value = 1400.0  # +300s (5 min bad)
            result = manager.process_posture_update('good', True)
            assert result['should_alert'] is False
            assert result.get('posture_corrected') is not True  # No confirmation

            # Cycle 2: good → bad → good (3 minutes)
            mock_time.return_value = 1500.0  # +100s
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False

            mock_time.return_value = 1680.0  # +180s (3 min bad)
            result = manager.process_posture_update('good', True)
            assert result['should_alert'] is False
            assert result.get('posture_corrected') is not True  # No confirmation

            # Verify no alert state was created
            assert manager.last_alert_time is None

    def test_socketio_events_emitted_during_alert_flow(self, manager):
        """Test SocketIO events are emitted during alert flow (AC1, AC2, Story 3.3).

        Validates:
        - AlertManager returns should_alert=True at threshold
        - AlertManager returns posture_corrected=True at correction
        - These flags would trigger SocketIO emissions in CV pipeline

        Note: This test validates AlertManager integration points.
        CV pipeline (app/cv/pipeline.py:389, 410) emits actual SocketIO events.
        """
        with patch('app.alerts.manager.time.time') as mock_time:
            # Simulate alert flow: bad posture → alert → correction

            # Start: bad posture detected
            mock_time.return_value = 1000.0
            result = manager.process_posture_update('bad', True)
            assert result['should_alert'] is False  # Under threshold

            # 10 minutes later: alert triggered
            mock_time.return_value = 1600.0  # +600s
            result = manager.process_posture_update('bad', True)

            # Verify AlertManager returns flag for SocketIO emission
            assert result['should_alert'] is True  # Would trigger alert_triggered event
            assert result['threshold_reached'] is True
            assert result['duration'] == 600

            # Expected SocketIO payload structure (from app/cv/pipeline.py:389-393):
            # socketio.emit('alert_triggered', {
            #     'message': f"Bad posture detected for {duration // 60} minutes",
            #     'duration': duration,
            #     'timestamp': datetime.now().isoformat()
            # }, broadcast=True)

            # Correction: posture becomes good
            mock_time.return_value = 1650.0  # +50s
            result = manager.process_posture_update('good', True)

            # Verify AlertManager returns flag for SocketIO emission
            assert result.get('posture_corrected') is True  # Would trigger posture_corrected event
            assert result.get('previous_duration') == 650

            # Expected SocketIO payload structure (from app/cv/pipeline.py:410-414):
            # socketio.emit('posture_corrected', {
            #     'message': '✓ Good posture restored! Nice work!',
            #     'previous_duration': previous_duration,
            #     'timestamp': datetime.now().isoformat()
            # }, broadcast=True)

            # Verify state reset after correction
            assert manager.bad_posture_start_time is None
            assert manager.last_alert_time is None
