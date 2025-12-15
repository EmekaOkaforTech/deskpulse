"""
Tests for posture correction confirmation feedback.

Story 3.5: Posture Correction Confirmation Feedback
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from app.alerts.manager import AlertManager
from app.alerts.notifier import send_confirmation


class TestAlertManagerCorrectionDetection:
    """Test AlertManager correction detection logic (AC1, AC5, AC6)."""

    @pytest.fixture
    def manager(self, app):
        """Create AlertManager instance with test config."""
        with app.app_context():
            return AlertManager()

    def test_correction_after_alert_returns_posture_corrected(self, manager):
        """Test: bad → alert → good returns posture_corrected=True (AC1)."""
        # Simulate bad posture for 10+ minutes
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start: bad posture detected
            mock_time.return_value = 1000.0
            result1 = manager.process_posture_update('bad', True)
            assert result1['should_alert'] is False  # Under threshold
            assert result1['duration'] == 0

            # 10 minutes later: alert triggered
            mock_time.return_value = 1720.0  # +720s (12 min)
            result2 = manager.process_posture_update('bad', True)
            assert result2['should_alert'] is True  # Alert triggered
            assert result2['duration'] == 720

            # Correction: posture becomes good
            mock_time.return_value = 1750.0  # +30s later
            result3 = manager.process_posture_update('good', True)

            # Should detect correction
            assert result3.get('posture_corrected') is True
            assert result3.get('previous_duration') == 750  # Total bad duration
            assert result3['should_alert'] is False
            assert result3['duration'] == 0
            assert result3['threshold_reached'] is False

            # State should be reset
            assert manager.bad_posture_start_time is None
            assert manager.last_alert_time is None

    def test_good_posture_without_alert_no_confirmation(self, manager):
        """Test: bad → good without alert returns posture_corrected=False (AC5)."""
        with patch('app.alerts.manager.time.time') as mock_time:
            # Start: bad posture detected
            mock_time.return_value = 1000.0
            manager.process_posture_update('bad', True)

            # 5 minutes later: posture corrected (before alert threshold)
            mock_time.return_value = 1300.0  # +300s (5 min)
            result = manager.process_posture_update('good', True)

            # Should NOT detect correction (no alert was sent)
            assert result.get('posture_corrected') is not True
            assert 'previous_duration' not in result
            assert result['should_alert'] is False

    def test_correction_state_reset_prevents_double_trigger(self, manager):
        """Test: State reset after correction prevents double-triggering (AC1)."""
        with patch('app.alerts.manager.time.time') as mock_time:
            # Trigger alert and correction
            mock_time.return_value = 1000.0
            manager.process_posture_update('bad', True)

            mock_time.return_value = 1720.0
            manager.process_posture_update('bad', True)  # Alert triggered

            mock_time.return_value = 1750.0
            result1 = manager.process_posture_update('good', True)
            assert result1.get('posture_corrected') is True

            # Immediate second "good" update should NOT trigger correction
            mock_time.return_value = 1760.0
            result2 = manager.process_posture_update('good', True)
            assert result2.get('posture_corrected') is not True

    def test_pause_resume_prevents_false_confirmation(self, manager):
        """Test: Pause during bad posture prevents confirmation after resume (AC6)."""
        with patch('app.alerts.manager.time.time') as mock_time:
            # Bad posture + alert
            mock_time.return_value = 1000.0
            manager.process_posture_update('bad', True)

            mock_time.return_value = 1720.0
            manager.process_posture_update('bad', True)  # Alert triggered

            # User pauses monitoring
            manager.pause_monitoring()

            # State should be reset
            assert manager.bad_posture_start_time is None
            assert manager.last_alert_time is None

            # Resume and correct posture
            manager.resume_monitoring()
            result = manager.process_posture_update('good', True)

            # Should NOT detect correction (state was reset)
            assert result.get('posture_corrected') is not True


class TestSendConfirmation:
    """Test send_confirmation() desktop notification function (AC2)."""

    @patch('app.alerts.notifier.send_desktop_notification')
    def test_send_confirmation_desktop_notification(self, mock_desktop):
        """Test: send_confirmation() sends desktop notification with correct message."""
        mock_desktop.return_value = True

        result = send_confirmation(720)  # 12 minutes

        # Should call send_desktop_notification
        mock_desktop.assert_called_once_with(
            "DeskPulse",
            "✓ Good posture restored! Nice work!"
        )

        # Should return success status
        assert result is True

    @patch('app.alerts.notifier.send_desktop_notification')
    def test_send_confirmation_return_value_reflects_success(self, mock_desktop):
        """Test: send_confirmation() return value reflects notification success."""
        # Test failure case
        mock_desktop.return_value = False
        result = send_confirmation(600)
        assert result is False

        # Test success case
        mock_desktop.return_value = True
        result = send_confirmation(600)
        assert result is True

    @patch('app.alerts.notifier.send_desktop_notification')
    @patch('app.alerts.notifier.logger')
    def test_send_confirmation_logging(self, mock_logger, mock_desktop):
        """Test: send_confirmation() logs duration and success status."""
        mock_desktop.return_value = True

        send_confirmation(720)  # 12 minutes

        # Should log confirmation with duration
        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        assert "12m" in log_message
        assert "desktop_sent=True" in log_message
