"""Repository unit tests for posture event persistence."""

import pytest
import time
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch
import sqlite3
from app.data.repository import PostureEventRepository


def test_insert_posture_event_good(app):
    """Test inserting 'good' posture event."""
    with app.app_context():
        event_id = PostureEventRepository.insert_posture_event(
            posture_state='good',
            user_present=True,
            confidence_score=0.92
        )

        assert event_id > 0

        # Verify event was stored
        events = PostureEventRepository.get_events_for_date(date.today())
        assert len(events) >= 1
        assert any(e['id'] == event_id for e in events)
        assert any(e['posture_state'] == 'good' for e in events)


def test_insert_posture_event_bad(app):
    """Test inserting 'bad' posture event."""
    with app.app_context():
        event_id = PostureEventRepository.insert_posture_event(
            posture_state='bad',
            user_present=True,
            confidence_score=0.85
        )

        assert event_id > 0

        # Verify event was stored
        events = PostureEventRepository.get_events_for_date(date.today())
        assert any(e['id'] == event_id and e['posture_state'] == 'bad' for e in events)


def test_insert_posture_event_with_metadata(app):
    """Test inserting posture event with JSON metadata."""
    with app.app_context():
        metadata = {'pain_level': 3, 'test_flag': True}
        event_id = PostureEventRepository.insert_posture_event(
            posture_state='bad',
            user_present=True,
            confidence_score=0.85,
            metadata=metadata
        )

        events = PostureEventRepository.get_events_for_date(date.today())
        event = next(e for e in events if e['id'] == event_id)

        assert event['metadata'] == metadata


def test_insert_posture_event_invalid_state(app):
    """Test inserting invalid posture state raises ValueError."""
    with app.app_context():
        with pytest.raises(ValueError, match="Invalid posture_state"):
            PostureEventRepository.insert_posture_event(
                posture_state='unknown',
                user_present=True,
                confidence_score=0.5
            )


def test_insert_posture_event_database_error(app):
    """Test graceful handling of database write failure."""
    with app.app_context():
        with patch('app.data.repository.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.execute.side_effect = sqlite3.Error("Disk full")
            mock_get_db.return_value = mock_db

            with pytest.raises(sqlite3.Error):
                PostureEventRepository.insert_posture_event('bad', True, 0.9)


def test_get_events_for_date_empty(app):
    """Test querying date with no events."""
    with app.app_context():
        # Query a date far in the past (no events should exist)
        past_date = date(2020, 1, 1)
        events = PostureEventRepository.get_events_for_date(past_date)

        assert events == []


def test_get_events_for_date_multiple(app):
    """Test querying date with multiple events."""
    with app.app_context():
        # Insert multiple events
        event_ids = []
        for state in ['good', 'bad', 'good']:
            event_id = PostureEventRepository.insert_posture_event(
                posture_state=state,
                user_present=True,
                confidence_score=0.9
            )
            event_ids.append(event_id)

        # Query today's events
        events = PostureEventRepository.get_events_for_date(date.today())

        # Should have at least the 3 we just inserted
        assert len(events) >= 3

        # Verify our events are in the results
        returned_ids = [e['id'] for e in events]
        for event_id in event_ids:
            assert event_id in returned_ids


def test_get_events_for_date_ordering(app):
    """Test events returned in timestamp ASC order."""
    with app.app_context():
        # Insert multiple events
        for state in ['good', 'bad', 'good']:
            PostureEventRepository.insert_posture_event(
                posture_state=state,
                user_present=True,
                confidence_score=0.9
            )
            # Small delay to ensure different timestamps
            time.sleep(0.01)

        events = PostureEventRepository.get_events_for_date(date.today())

        # Verify ascending timestamp order
        timestamps = [e['timestamp'] for e in events]
        assert timestamps == sorted(timestamps)


def test_get_events_for_date_boundary(app):
    """Test date range boundary (00:00:00 to 23:59:59)."""
    with app.app_context():
        # Insert event
        event_id = PostureEventRepository.insert_posture_event(
            posture_state='good',
            user_present=True,
            confidence_score=0.92
        )

        # Query today - should find the event
        today_events = PostureEventRepository.get_events_for_date(date.today())
        assert any(e['id'] == event_id for e in today_events)

        # Query tomorrow - should NOT find the event
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_events = PostureEventRepository.get_events_for_date(tomorrow)
        assert not any(e['id'] == event_id for e in tomorrow_events)

        # Query yesterday - should NOT find the event
        yesterday = date.today() - timedelta(days=1)
        yesterday_events = PostureEventRepository.get_events_for_date(yesterday)
        assert not any(e['id'] == event_id for e in yesterday_events)


def test_insert_posture_event_performance(app):
    """Verify database write latency <20ms (acceptable for 10 FPS = 100ms per frame)."""
    with app.app_context():
        start_time = time.perf_counter()

        event_id = PostureEventRepository.insert_posture_event(
            posture_state='bad',
            user_present=True,
            confidence_score=0.87
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert event_id > 0
        # Raspberry Pi hardware under test load: <20ms is acceptable for 10 FPS (100ms per frame)
        # Write takes <20% of frame budget, CV pipeline not blocked
        # Typical: 6-10ms, but can spike to 15-20ms under system load
        assert elapsed_ms < 20.0, f"Write took {elapsed_ms:.2f}ms (expected <20ms)"


def test_insert_batch_performance_regression(app):
    """Verify 100 sequential writes complete in <500ms (regression test for Raspberry Pi)."""
    with app.app_context():
        start_time = time.perf_counter()

        for i in range(100):
            PostureEventRepository.insert_posture_event(
                posture_state='bad' if i % 2 == 0 else 'good',
                user_present=True,
                confidence_score=0.87
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Raspberry Pi: ~240ms for 100 writes = 2.4ms/write average
        # Acceptable for expected load (~10 events/day, not continuous writes)
        assert elapsed_ms < 500.0, f"100 writes took {elapsed_ms:.2f}ms (expected <500ms)"


def test_insert_posture_event_user_absent(app):
    """Test inserting event with user_present=False."""
    with app.app_context():
        event_id = PostureEventRepository.insert_posture_event(
            posture_state='bad',
            user_present=False,  # User not present
            confidence_score=0.0
        )

        assert event_id > 0

        # Verify event was stored with user_present=False
        events = PostureEventRepository.get_events_for_date(date.today())
        event = next(e for e in events if e['id'] == event_id)

        assert event['user_present'] is False
        assert event['posture_state'] == 'bad'
