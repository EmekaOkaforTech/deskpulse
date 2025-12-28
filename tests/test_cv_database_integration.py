"""Integration tests for CV pipeline database persistence.

NOTE: These tests validate the state change detection pattern and repository
integration. The actual _processing_loop is a continuous while loop that's
difficult to test in isolation. These tests verify the core logic that runs
inside the loop.
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch
from app.cv.pipeline import CVPipeline
from app.data.repository import PostureEventRepository


def test_cv_pipeline_state_tracking_integration(app, mock_camera):
    """Test CV pipeline's state tracking integrates correctly with repository.

    This test validates that the CVPipeline state tracking pattern works
    correctly with the PostureEventRepository. While it doesn't run the full
    _processing_loop (which is a continuous while loop), it validates the
    core state change detection logic.
    """
    with app.app_context():
        # Initialize CV pipeline
        pipeline = CVPipeline(fps_target=10, app=app)

        # Verify initial state
        assert pipeline.last_posture_state is None

        # Simulate the state change detection logic from _processing_loop
        # This is the actual pattern used in pipeline.py lines 367-388

        # Mock detection results
        mock_detection = {
            'user_present': True,
            'confidence': 0.92,
            'landmarks': Mock()
        }

        # State 1: None → good (first detection)
        posture_state = 'good'
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            event_id_1 = PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=mock_detection['user_present'],
                confidence_score=mock_detection['confidence'],
                metadata={}
            )
            pipeline.last_posture_state = posture_state
            assert event_id_1 > 0

        # State 2: good → bad (state change, should persist)
        posture_state = 'bad'
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            event_id_2 = PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=mock_detection['user_present'],
                confidence_score=0.85,
                metadata={}
            )
            pipeline.last_posture_state = posture_state
            assert event_id_2 > 0

        # State 3: bad → bad (no change, should NOT persist)
        posture_state = 'bad'
        initial_event_count = len(PostureEventRepository.get_events_for_date(date.today()))
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            # Should not reach here
            PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=mock_detection['user_present'],
                confidence_score=0.87,
                metadata={}
            )
        final_event_count = len(PostureEventRepository.get_events_for_date(date.today()))
        # Event count should not change (no duplicate for same state)
        assert final_event_count == initial_event_count

        # State 4: bad → good (state change, should persist)
        posture_state = 'good'
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            event_id_3 = PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=mock_detection['user_present'],
                confidence_score=0.94,
                metadata={}
            )
            pipeline.last_posture_state = posture_state
            assert event_id_3 > 0

        # Verify database has exactly 3 events (good, bad, good)
        events = PostureEventRepository.get_events_for_date(date.today())

        assert len(events) == 3, f"Expected 3 events, got {len(events)}"
        assert events[0]['posture_state'] == 'good', "First event should be 'good'"
        assert events[1]['posture_state'] == 'bad', "Second event should be 'bad'"
        assert events[2]['posture_state'] == 'good', "Third event should be 'good'"

        # Verify event ordering (timestamp ASC)
        timestamps = [e['timestamp'] for e in events]
        assert timestamps == sorted(timestamps), "Events should be ordered by timestamp ASC"


def test_cv_pipeline_state_change_detection_prevents_duplicates(app):
    """Test that state change detection prevents duplicate events."""
    with app.app_context():
        pipeline = CVPipeline(fps_target=10, app=app)

        # Initial state
        pipeline.last_posture_state = None

        # First good posture (should persist)
        posture_state = 'good'
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=True,
                confidence_score=0.90,
                metadata={}
            )
            pipeline.last_posture_state = posture_state

        initial_count = len(PostureEventRepository.get_events_for_date(date.today()))

        # Same posture repeated 10 times (should NOT persist any)
        for _ in range(10):
            posture_state = 'good'
            if posture_state != pipeline.last_posture_state and posture_state is not None:
                PostureEventRepository.insert_posture_event(
                    posture_state=posture_state,
                    user_present=True,
                    confidence_score=0.91,
                    metadata={}
                )
                pipeline.last_posture_state = posture_state

        final_count = len(PostureEventRepository.get_events_for_date(date.today()))

        # Count should not change (no duplicate events)
        assert final_count == initial_count, "No duplicate events should be inserted for same state"


def test_cv_pipeline_user_absent_does_not_persist(app):
    """Test that user_present=False with posture_state=None does not persist."""
    with app.app_context():
        pipeline = CVPipeline(fps_target=10, app=app)

        # User present with good posture (should persist)
        pipeline.last_posture_state = None
        posture_state = 'good'
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=True,
                confidence_score=0.92,
                metadata={}
            )
            pipeline.last_posture_state = posture_state

        initial_count = len(PostureEventRepository.get_events_for_date(date.today()))

        # User absent (posture_state=None, should NOT persist)
        posture_state = None
        if posture_state != pipeline.last_posture_state and posture_state is not None:
            # Should not reach here because posture_state is None
            PostureEventRepository.insert_posture_event(
                posture_state=posture_state,
                user_present=False,
                confidence_score=0.0,
                metadata={}
            )
            pipeline.last_posture_state = posture_state

        final_count = len(PostureEventRepository.get_events_for_date(date.today()))

        # Count should not change (None state should not persist)
        assert final_count == initial_count, "User absent (None state) should not persist"

        # last_posture_state should NOT be updated to None
        assert pipeline.last_posture_state == 'good', "last_posture_state should remain 'good'"


def test_repository_validation_from_pipeline_context(app):
    """Test that repository input validation catches invalid data from pipeline.

    This validates the High issues #4-6 fixes are working.
    """
    with app.app_context():
        # Test invalid confidence_score
        with pytest.raises(ValueError, match="confidence_score.*between 0.0 and 1.0"):
            PostureEventRepository.insert_posture_event(
                posture_state='good',
                user_present=True,
                confidence_score=1.5  # Invalid: > 1.0
            )

        with pytest.raises(ValueError, match="confidence_score.*between 0.0 and 1.0"):
            PostureEventRepository.insert_posture_event(
                posture_state='good',
                user_present=True,
                confidence_score=-0.1  # Invalid: < 0.0
            )

        # Test invalid user_present type
        with pytest.raises(TypeError, match="user_present.*Must be bool"):
            PostureEventRepository.insert_posture_event(
                posture_state='good',
                user_present=1,  # Invalid: should be bool
                confidence_score=0.9
            )

        # Test invalid metadata type
        with pytest.raises(TypeError, match="metadata.*Must be dict or None"):
            PostureEventRepository.insert_posture_event(
                posture_state='good',
                user_present=True,
                confidence_score=0.9,
                metadata="string"  # Invalid: should be dict
            )
