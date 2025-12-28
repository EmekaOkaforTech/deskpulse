"""Unit tests for PostureAnalytics.generate_daily_summary() method.

Story 4.6: End-of-Day Summary Report

Test Coverage:
- Normal summary generation with data
- Day-over-day comparisons (improving, declining, stable)
- Score tier motivational messages (≥75%, ≥50%, ≥30%, <30%)
- Edge cases (no data today, no data yesterday, zero events, single event)
- Date formatting and emoji inclusion
- Type validation and error handling
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch
from app.data.analytics import PostureAnalytics
from app.data.repository import PostureEventRepository


def test_normal_summary_with_data(app):
    """Test summary generation with typical posture data."""
    with app.app_context():
        from unittest.mock import patch

        today = date(2025, 12, 28)
        yesterday = date(2025, 12, 27)

        # Create realistic posture data
        with patch('app.data.repository.datetime') as mock_dt:
            # Yesterday: 50% good posture
            base = datetime.combine(yesterday, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=20000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

            # Today: ~71% good posture (18000 good, 7200 bad)
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=18000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=25200)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Assertions
        assert isinstance(summary, str)
        assert "📊 DeskPulse Daily Summary - Sunday, December 28" in summary
        assert "Posture Score:" in summary
        assert "Good Posture:" in summary
        assert "Bad Posture:" in summary


def test_improving_score(app):
    """Test summary with improving score (>+5 points)."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)
            yesterday = date(2025, 12, 27)

            # Yesterday: 50% good posture
            base = datetime.combine(yesterday, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=5000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

            # Today: 80% good posture (improvement)
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=8000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should show improvement message
        assert "✨ Improvement:" in summary
        assert "points from yesterday!" in summary


def test_declining_score(app):
    """Test summary with declining score (<-5 points)."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)
            yesterday = date(2025, 12, 27)

            # Yesterday: 70% good posture
            base = datetime.combine(yesterday, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=7000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

            # Today: 30% good posture (decline)
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=3000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should show decline message
        assert "📉 Change:" in summary
        assert "points from yesterday" in summary


def test_stable_score(app):
    """Test summary with stable score (-5 to +5 points)."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)
            yesterday = date(2025, 12, 27)

            # Yesterday: 60% good posture
            base = datetime.combine(yesterday, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=6000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

            # Today: 62% good posture (stable)
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=6200)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should show consistent message
        assert "→ Consistent:" in summary
        assert "Similar to yesterday" in summary


def test_no_data_today(app):
    """Test summary when no data exists for today."""
    with app.app_context():
        today = date(2025, 12, 28)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should show no data message
        assert "No posture data collected today." in summary
        assert "🔔 Make sure monitoring is running tomorrow!" in summary


def test_no_data_yesterday(app):
    """Test summary when today has data but yesterday doesn't."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            # Today only: 50% good posture
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=5000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should compare to 0% for yesterday
        assert "Posture Score:" in summary
        # Should show improvement since yesterday was 0%
        assert "✨ Improvement:" in summary


def test_score_tier_excellent(app):
    """Test motivational message for score ≥75%."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            # 80% good posture
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=8000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        summary = PostureAnalytics.generate_daily_summary(today)

        assert "🎉 Excellent work! Your posture was great today." in summary


def test_score_tier_good(app):
    """Test motivational message for 50% ≤ score < 75%."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            # 60% good posture
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=6000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        assert "👍 Good job! Keep building on this progress." in summary


def test_score_tier_room_for_improvement(app):
    """Test motivational message for 30% ≤ score < 50%."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            # 40% good posture
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=4000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        assert "💪 Room for improvement. Focus on posture during work sessions tomorrow." in summary


def test_score_tier_needs_work(app):
    """Test motivational message for score < 30%."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            # 20% good posture
            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=2000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)
            mock_dt.now.return_value = base + timedelta(seconds=10000)
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        assert "🔔 Let's work on better posture tomorrow. You've got this!" in summary


def test_date_formatting(app):
    """Test that date is formatted correctly with day and month name."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 1, 15)  # Wednesday

            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=5000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Check date format: "Wednesday, January 15"
        assert "Wednesday, January 15" in summary


def test_single_event(app):
    """Test summary with only one event."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should show 100% posture score
        assert "Posture Score: 100.0%" in summary
        assert "🎉 Excellent work!" in summary


def test_default_date_today(app):
    """Test that default target_date is today."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date.today()

            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=5000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        # Call without target_date argument
        summary = PostureAnalytics.generate_daily_summary()

        assert "📊 DeskPulse Daily Summary" in summary
        assert "Posture Score:" in summary


def test_invalid_target_date_type(app_context):
    """Test TypeError when target_date is not a date object."""
    with pytest.raises(TypeError, match="target_date must be datetime.date object"):
        PostureAnalytics.generate_daily_summary("2025-12-28")


def test_datetime_instead_of_date(app_context):
    """Test TypeError when datetime object is passed instead of date."""
    with pytest.raises(TypeError, match="target_date must be date object, not datetime"):
        PostureAnalytics.generate_daily_summary(datetime(2025, 12, 28, 10, 30))


def test_emoji_inclusion(app):
    """Test that summary includes all expected emojis."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=8000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Check for emoji inclusion
        assert "📊" in summary  # Dashboard emoji in title
        # At least one motivational emoji should be present
        assert any(emoji in summary for emoji in ["✨", "👍", "🎉", "💪", "🔔", "📉"])


def test_multiline_format(app):
    """Test that summary is formatted as multi-line string."""
    with app.app_context():
        with patch('app.data.repository.datetime') as mock_dt:
            today = date(2025, 12, 28)

            base = datetime.combine(today, datetime.min.time())
            mock_dt.now.return_value = base
            PostureEventRepository.insert_posture_event('good', True, 0.9)
            mock_dt.now.return_value = base + timedelta(seconds=5000)
            PostureEventRepository.insert_posture_event('bad', True, 0.85)

        summary = PostureAnalytics.generate_daily_summary(today)

        # Should have multiple lines
        lines = summary.split('\n')
        assert len(lines) > 5  # At least title, blank, score, durations, blank, motivation
