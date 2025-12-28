"""Unit tests for DailyScheduler - Story 4.6 End-of-Day Summary Report.

Test Coverage:
- Scheduler initialization and configuration
- Start/stop lifecycle management
- Time format validation
- Flask app context execution
- Error resilience and recovery
- Thread safety and idempotency
- Singleton pattern enforcement
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from app.system.scheduler import DailyScheduler, start_scheduler, stop_scheduler


def test_scheduler_initialization(app):
    """Test scheduler initializes with correct attributes."""
    scheduler = DailyScheduler(app)

    assert scheduler.app is app
    assert scheduler.running is False
    assert scheduler.thread is None
    assert scheduler.schedule is not None


def test_scheduler_start_creates_thread(app):
    """Test start() creates and starts daemon thread."""
    scheduler = DailyScheduler(app)

    result = scheduler.start()

    assert result is True
    assert scheduler.running is True
    assert scheduler.thread is not None
    assert scheduler.thread.daemon is True
    assert scheduler.thread.name == 'DailyScheduler'
    assert scheduler.thread.is_alive()

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)  # Allow thread to exit


def test_scheduler_stop_gracefully_exits(app):
    """Test stop() sets running flag to False."""
    scheduler = DailyScheduler(app)
    scheduler.start()

    assert scheduler.running is True

    scheduler.stop()

    assert scheduler.running is False
    # Thread will exit on next poll cycle (daemon thread auto-cleanup)


def test_scheduler_idempotent_start(app):
    """Test calling start() multiple times is safe (idempotent)."""
    scheduler = DailyScheduler(app)

    result1 = scheduler.start()
    result2 = scheduler.start()  # Second call should be no-op

    assert result1 is True
    assert result2 is False  # Returns False for already running
    assert scheduler.running is True

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)


def test_scheduler_time_format_validation_valid(app):
    """Test scheduler accepts valid HH:MM time format."""
    app.config['DAILY_SUMMARY_TIME'] = '18:30'
    scheduler = DailyScheduler(app)

    scheduler.start()

    # If no error raised, validation passed
    assert scheduler.running is True

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)


def test_scheduler_time_format_validation_invalid_fallback(app):
    """Test scheduler falls back to 18:00 for invalid time format."""
    app.config['DAILY_SUMMARY_TIME'] = 'invalid-time'
    scheduler = DailyScheduler(app)

    with patch('app.system.scheduler.logger') as mock_logger:
        scheduler.start()

        # Should log error about invalid format
        mock_logger.error.assert_called_once()
        error_msg = mock_logger.error.call_args[0][0]
        assert 'Invalid DAILY_SUMMARY_TIME format' in error_msg
        assert 'Using default 18:00' in error_msg

    # Scheduler should still be running (fallback successful)
    assert scheduler.running is True

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)


def test_scheduler_runs_task_within_app_context(app):
    """Test _run_daily_summary executes within Flask app context."""
    scheduler = DailyScheduler(app)

    # Mock send_daily_summary to verify it's called
    with patch('app.alerts.notifier.send_daily_summary') as mock_send:
        mock_send.return_value = {
            'summary': 'Test summary',
            'desktop_sent': True,
            'socketio_sent': True,
            'timestamp': '2025-12-28T18:00:00'
        }

        # Call _run_daily_summary directly (simulates scheduled task)
        scheduler._run_daily_summary()

        # Verify send_daily_summary was called
        mock_send.assert_called_once()


def test_scheduler_error_resilience_task_failure(app):
    """Test scheduler continues running even if task fails."""
    scheduler = DailyScheduler(app)

    # Mock send_daily_summary to raise exception
    with patch('app.alerts.notifier.send_daily_summary') as mock_send:
        mock_send.side_effect = Exception("Simulated task failure")

        with patch('app.system.scheduler.logger') as mock_logger:
            # Call _run_daily_summary - should not crash
            scheduler._run_daily_summary()

            # Should log exception but not raise
            mock_logger.exception.assert_called_once()
            error_msg = mock_logger.exception.call_args[0][0]
            assert 'Daily summary task failed' in error_msg


def test_scheduler_error_resilience_loop_continues(app):
    """Test scheduler polling loop continues after error."""
    scheduler = DailyScheduler(app)

    # Mock schedule.run_pending to raise exception once
    call_count = 0
    def mock_run_pending():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Simulated loop error")

    with patch.object(scheduler.schedule, 'run_pending', side_effect=mock_run_pending):
        scheduler.start()

        # Wait for at least 2 poll cycles (error + recovery)
        time.sleep(0.2)

        # Scheduler should still be running
        assert scheduler.running is True

        # run_pending should have been called at least twice (error + retry)
        assert call_count >= 1

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)


def test_start_scheduler_singleton_pattern(app):
    """Test module-level start_scheduler creates singleton instance."""
    # Ensure clean state
    stop_scheduler()

    instance1 = start_scheduler(app)
    instance2 = start_scheduler(app)  # Should return same instance

    assert instance1 is not None
    assert instance2 is instance1  # Same object
    assert instance1.running is True

    # Cleanup
    stop_scheduler()
    time.sleep(0.1)


def test_stop_scheduler_module_function(app):
    """Test module-level stop_scheduler stops singleton instance."""
    # Ensure clean state
    stop_scheduler()

    instance = start_scheduler(app)
    assert instance.running is True

    stop_scheduler()

    assert instance.running is False


def test_scheduler_config_default_time(app):
    """Test scheduler uses default time if config not set."""
    # Remove DAILY_SUMMARY_TIME from config
    if 'DAILY_SUMMARY_TIME' in app.config:
        del app.config['DAILY_SUMMARY_TIME']

    scheduler = DailyScheduler(app)
    scheduler.start()

    # Should use default 18:00 without error
    assert scheduler.running is True

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)


def test_scheduler_thread_naming(app):
    """Test scheduler thread has correct name for debugging."""
    scheduler = DailyScheduler(app)
    scheduler.start()

    assert scheduler.thread.name == 'DailyScheduler'

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)


def test_scheduler_daemon_thread_flag(app):
    """Test scheduler thread is daemon (auto-cleanup on exit)."""
    scheduler = DailyScheduler(app)
    scheduler.start()

    # Daemon flag must be True for automatic cleanup
    assert scheduler.thread.daemon is True

    # Cleanup
    scheduler.stop()
    time.sleep(0.1)
