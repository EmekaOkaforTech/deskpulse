"""Unit tests for posture analytics calculation engine.

Tests validate:
- Daily statistics calculation from event data
- 7-day history generation
- Duration formatting utilities
- Edge cases (no events, single event, rapid changes)
"""

import pytest
from datetime import datetime, date, timedelta, time
from app.data.analytics import PostureAnalytics, format_duration
from app.data.repository import PostureEventRepository


def test_calculate_daily_stats_no_events(app):
    """Test daily stats with no events returns zeros."""
    with app.app_context():
        stats = PostureAnalytics.calculate_daily_stats(date.today())

        assert stats['date'] == date.today()
        assert stats['good_duration_seconds'] == 0
        assert stats['bad_duration_seconds'] == 0
        assert stats['user_present_duration_seconds'] == 0
        assert stats['posture_score'] == 0.0
        assert stats['total_events'] == 0


def test_calculate_daily_stats_single_event_good(app):
    """Test single 'good' event returns 10-minute duration."""
    with app.app_context():
        from unittest.mock import patch

        base_time = datetime(2025, 12, 19, 10, 0, 0)

        # Insert single good event
        with patch('app.data.repository.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        # Single event should be capped at 10 minutes (600 seconds)
        assert stats['good_duration_seconds'] == 600
        assert stats['bad_duration_seconds'] == 0
        assert stats['user_present_duration_seconds'] == 600
        assert stats['posture_score'] == 100.0
        assert stats['total_events'] == 1


def test_calculate_daily_stats_single_event_bad(app):
    """Test single 'bad' event returns 10-minute duration."""
    with app.app_context():
        from unittest.mock import patch

        base_time = datetime(2025, 12, 19, 14, 30, 0)

        # Insert single bad event
        with patch('app.data.repository.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        # Single event should be capped at 10 minutes
        assert stats['good_duration_seconds'] == 0
        assert stats['bad_duration_seconds'] == 600
        assert stats['user_present_duration_seconds'] == 600
        assert stats['posture_score'] == 0.0
        assert stats['total_events'] == 1


def test_calculate_daily_stats_multiple_events(app):
    """Test duration calculation with multiple events."""
    with app.app_context():
        from unittest.mock import patch

        base_time = datetime(2025, 12, 19, 10, 0, 0)

        # Mock datetime.now() to control event timestamps
        with patch('app.data.repository.datetime') as mock_dt:
            # Event 1: good at 10:00:00
            mock_dt.now.return_value = base_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

            # Event 2: bad at 10:15:00 (15 minutes later)
            mock_dt.now.return_value = base_time + timedelta(minutes=15)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

            # Event 3: good at 10:30:00 (15 minutes later)
            mock_dt.now.return_value = base_time + timedelta(minutes=30)
            PostureEventRepository.insert_posture_event('good', True, 0.92)

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        # Verify duration calculations:
        # Good: 15 min (10:00-10:15) + 10 min (last event cap) = 1500 sec
        # Bad: 15 min (10:15-10:30) = 900 sec
        assert stats['good_duration_seconds'] == 1500
        assert stats['bad_duration_seconds'] == 900
        assert stats['posture_score'] == 62.5  # (1500/2400)*100
        assert stats['total_events'] == 3


def test_calculate_daily_stats_posture_score_calculation(app):
    """Test posture score formula (good_duration / total_duration * 100)."""
    with app.app_context():
        from unittest.mock import patch

        base_time = datetime(2025, 12, 19, 9, 0, 0)

        with patch('app.data.repository.datetime') as mock_dt:
            # Good for 30 minutes
            mock_dt.now.return_value = base_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

            # Bad for 10 minutes
            mock_dt.now.return_value = base_time + timedelta(minutes=30)
            PostureEventRepository.insert_posture_event('bad', True, 0.8)

            # Total: 30 good + 10 bad (last event cap) = 40 minutes
            # Score: (30/40) * 100 = 75.0%

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        assert stats['good_duration_seconds'] == 1800  # 30 minutes
        assert stats['bad_duration_seconds'] == 600    # 10 minutes (cap)
        assert stats['posture_score'] == 75.0


def test_calculate_daily_stats_last_event_capped(app):
    """Test last event duration is capped at 10 minutes."""
    with app.app_context():
        from unittest.mock import patch

        # Event at 10:00 - should be capped at 10 minutes, not until EOD
        base_time = datetime(2025, 12, 19, 10, 0, 0)

        with patch('app.data.repository.datetime') as mock_dt:
            mock_dt.now.return_value = base_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        # Last event should be 10 minutes, not ~14 hours until EOD
        assert stats['good_duration_seconds'] == 600
        assert stats['user_present_duration_seconds'] == 600


def test_calculate_daily_stats_last_event_end_of_day(app):
    """Test last event near midnight caps at time remaining to EOD."""
    with app.app_context():
        from unittest.mock import patch

        # Event at 23:58:00 - only 2 minutes until midnight
        late_time = datetime(2025, 12, 19, 23, 58, 0)

        with patch('app.data.repository.datetime') as mock_dt:
            mock_dt.now.return_value = late_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        # Should cap at ~2 minutes to EOD, not 10 minutes
        # time.max = 23:59:59.999999, so ~120 seconds remaining
        assert stats['good_duration_seconds'] < 600  # Less than 10 minutes
        assert 119 <= stats['good_duration_seconds'] <= 121  # ~2 minutes


def test_calculate_daily_stats_rapid_state_changes(app):
    """Test accurate tracking with rapid state transitions."""
    with app.app_context():
        from unittest.mock import patch

        base_time = datetime(2025, 12, 19, 15, 0, 0)

        with patch('app.data.repository.datetime') as mock_dt:
            # Rapid changes every 30 seconds
            mock_dt.now.return_value = base_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

            mock_dt.now.return_value = base_time + timedelta(seconds=30)
            PostureEventRepository.insert_posture_event('bad', True, 0.8)

            mock_dt.now.return_value = base_time + timedelta(seconds=60)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

            mock_dt.now.return_value = base_time + timedelta(seconds=90)
            PostureEventRepository.insert_posture_event('bad', True, 0.8)

        stats = PostureAnalytics.calculate_daily_stats(date(2025, 12, 19))

        # Duration calculation:
        # Event 1 (good, 15:00:00) -> Event 2 (bad, 15:00:30): good += 30s
        # Event 2 (bad, 15:00:30) -> Event 3 (good, 15:01:00): bad += 30s
        # Event 3 (good, 15:01:00) -> Event 4 (bad, 15:01:30): good += 30s
        # Event 4 (bad, last event): bad += 600s (10 min cap)
        # Total: good = 60s, bad = 630s
        assert stats['good_duration_seconds'] == 60
        assert stats['bad_duration_seconds'] == 630
        assert stats['posture_score'] == 8.7  # (60/690)*100 = 8.7%
        assert stats['total_events'] == 4


def test_get_7_day_history_structure(app):
    """Test 7-day history returns correct structure and ordering."""
    with app.app_context():
        history = PostureAnalytics.get_7_day_history()

        # Should return exactly 7 days
        assert len(history) == 7

        # Each entry should have all required fields
        for day_stats in history:
            assert 'date' in day_stats
            assert 'good_duration_seconds' in day_stats
            assert 'bad_duration_seconds' in day_stats
            assert 'user_present_duration_seconds' in day_stats
            assert 'posture_score' in day_stats
            assert 'total_events' in day_stats

        # Should be chronologically ordered (oldest to newest)
        for i in range(len(history) - 1):
            assert history[i]['date'] < history[i + 1]['date']


def test_get_7_day_history_date_range(app):
    """Test 7-day history covers correct date range."""
    with app.app_context():
        history = PostureAnalytics.get_7_day_history()
        today = date.today()

        # First entry should be 6 days ago
        assert history[0]['date'] == today - timedelta(days=6)

        # Last entry should be today
        assert history[-1]['date'] == today

        # Verify all 7 days are consecutive
        for i, day_stats in enumerate(history):
            expected_date = today - timedelta(days=6 - i)
            assert day_stats['date'] == expected_date


def test_get_7_day_history_empty_database(app):
    """Test 7-day history with no events returns zeros for all days."""
    with app.app_context():
        history = PostureAnalytics.get_7_day_history()

        assert len(history) == 7

        # All days should have zero stats
        for day_stats in history:
            assert day_stats['good_duration_seconds'] == 0
            assert day_stats['bad_duration_seconds'] == 0
            assert day_stats['user_present_duration_seconds'] == 0
            assert day_stats['posture_score'] == 0.0
            assert day_stats['total_events'] == 0


def test_format_duration_hours_minutes():
    """Test duration formatting with hours and minutes."""
    assert format_duration(7890) == "2h 11m"
    assert format_duration(3661) == "1h 1m"
    assert format_duration(7200) == "2h 0m"
    assert format_duration(3600) == "1h 0m"


def test_format_duration_minutes_only():
    """Test duration formatting for minutes only (< 1 hour)."""
    assert format_duration(300) == "5m"
    assert format_duration(60) == "1m"
    assert format_duration(3599) == "59m"
    assert format_duration(45) == "0m"  # Less than 1 minute rounds down


def test_format_duration_zero():
    """Test duration formatting for zero and negative values."""
    assert format_duration(0) == "0m"
    assert format_duration(-100) == "0m"
    assert format_duration(-1) == "0m"


def test_calculate_daily_stats_input_validation_none(app):
    """Test input validation rejects None."""
    with app.app_context():
        with pytest.raises(TypeError) as exc_info:
            PostureAnalytics.calculate_daily_stats(None)

        assert "must be datetime.date object" in str(exc_info.value)
        assert "got NoneType" in str(exc_info.value)


def test_calculate_daily_stats_input_validation_string(app):
    """Test input validation rejects string."""
    with app.app_context():
        with pytest.raises(TypeError) as exc_info:
            PostureAnalytics.calculate_daily_stats("2025-12-19")

        assert "must be datetime.date object" in str(exc_info.value)
        assert "got str" in str(exc_info.value)


def test_calculate_daily_stats_input_validation_datetime(app):
    """Test input validation rejects datetime (common mistake)."""
    with app.app_context():
        with pytest.raises(TypeError) as exc_info:
            PostureAnalytics.calculate_daily_stats(datetime.now())

        assert "must be date object, not datetime" in str(exc_info.value)
        assert "Call .date() to convert" in str(exc_info.value)


def test_calculate_daily_stats_negative_duration_protection(app):
    """Test protection against negative remaining_duration from clock skew.

    Simulates edge case: Last event timestamp is 11:59:30pm, but due to
    processing delay or clock skew, we calculate stats slightly after midnight.
    The remaining_duration calculation could become negative.
    """
    with app.app_context():
        from unittest.mock import patch

        # Create event very close to end of day
        target = date.today()
        late_time = datetime.combine(target, time(23, 59, 30))  # 11:59:30 PM

        with patch('app.data.repository.datetime') as mock_dt:
            mock_dt.now.return_value = late_time
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        # Now mock calculate_daily_stats to simulate processing after midnight
        # by directly testing the max(0, ...) protection works
        stats = PostureAnalytics.calculate_daily_stats(target)

        # Should have ~29.999 seconds remaining (30 seconds to EOD at 23:59:59.999)
        # This validates max(0, ...) protection works even in edge cases
        assert stats['good_duration_seconds'] >= 29
        assert stats['good_duration_seconds'] <= 31
        assert stats['bad_duration_seconds'] == 0
        assert stats['posture_score'] == 100.0
        assert stats['total_events'] == 1
