"""Repository for posture event data access.

This module provides CRUD operations for posture_event table, abstracting
database access from the CV pipeline and analytics modules.

CRITICAL: All methods require Flask app context (get_db() dependency).
"""

import logging
import json
from datetime import datetime, date, time
from app.data.database import get_db

logger = logging.getLogger('deskpulse.db')


class PostureEventRepository:
    """Repository for posture event data access.

    CRITICAL: All methods require Flask app context.
    - CV Pipeline: Automatically has context via self.app
    - Tests: Must use app.app_context() or app_context fixture
    """

    @staticmethod
    def insert_posture_event(posture_state, user_present, confidence_score, metadata=None):
        """Insert new posture event. Returns event_id. Raises ValueError if invalid state.

        Args:
            posture_state: 'good' or 'bad' only
            user_present: bool
            confidence_score: float (0.0-1.0)
            metadata: dict (optional) - extensible JSON

        Metadata Schema Examples:
            {} - Story 4.1 (MVP empty dict)
            {'pain_level': 3, 'pain_location': 'lower_back'} - Growth feature FR20
            {'pain_level': 3, 'phone_detected': True} - Future multi-feature

        Query metadata: SELECT json_extract(metadata, '$.pain_level') FROM posture_event

        Returns:
            int: Event ID of inserted row

        Raises:
            ValueError: If posture_state not in ('good', 'bad')
            sqlite3.Error: If database write fails
        """
        # Validate posture_state
        if posture_state not in ('good', 'bad'):
            raise ValueError(f"Invalid posture_state: {posture_state}. Must be 'good' or 'bad'.")

        # Validate user_present is bool
        if not isinstance(user_present, bool):
            raise TypeError(f"Invalid user_present type: {type(user_present).__name__}. Must be bool.")

        # Validate confidence_score is in range [0.0, 1.0]
        if not isinstance(confidence_score, (int, float)):
            raise TypeError(f"Invalid confidence_score type: {type(confidence_score).__name__}. Must be float.")
        if not 0.0 <= confidence_score <= 1.0:
            raise ValueError(f"Invalid confidence_score: {confidence_score}. Must be between 0.0 and 1.0.")

        # Validate metadata is dict or None
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError(f"Invalid metadata type: {type(metadata).__name__}. Must be dict or None.")

        # Convert metadata to JSON string
        metadata_json = json.dumps(metadata if metadata is not None else {})

        # Get database connection
        db = get_db()

        # Insert event
        cursor = db.execute(
            """
            INSERT INTO posture_event (timestamp, posture_state, user_present, confidence_score, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.now(), posture_state, user_present, confidence_score, metadata_json)
        )
        db.commit()

        event_id = cursor.lastrowid
        logger.info(
            f"Posture event inserted: id={event_id}, state={posture_state}, "
            f"user_present={user_present}, confidence={confidence_score:.2f}"
        )

        return event_id

    @staticmethod
    def get_events_for_date(target_date):
        """Query events for date range (00:00:00-23:59:59). Returns list[dict] ordered by timestamp ASC.

        Args:
            target_date: date object

        Returns:
            list[dict]: Events with keys: id, timestamp, posture_state, user_present,
                        confidence_score, metadata

        Row Factory Usage (sqlite3.Row from get_db()):
            events = PostureEventRepository.get_events_for_date(date.today())
            for event in events:
                print(f"State: {event['posture_state']} at {event['timestamp']}")
        """
        # Calculate start and end datetime for the date range
        start_datetime = datetime.combine(target_date, time.min)  # 00:00:00
        end_datetime = datetime.combine(target_date, time.max)    # 23:59:59

        # Get database connection
        db = get_db()

        # Query events in date range
        cursor = db.execute(
            """
            SELECT id, timestamp, posture_state, user_present, confidence_score, metadata
            FROM posture_event
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
            """,
            (start_datetime, end_datetime)
        )

        # Convert rows to list of dicts
        events = []
        for row in cursor.fetchall():
            event = {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'posture_state': row['posture_state'],
                'user_present': bool(row['user_present']),
                'confidence_score': row['confidence_score'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {}
            }
            events.append(event)

        logger.debug(f"Retrieved {len(events)} events for date {target_date}")

        return events
