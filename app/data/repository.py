"""Repository for posture event and achievement data access.

This module provides CRUD operations for posture_event and achievement tables,
abstracting database access from the CV pipeline and analytics modules.

CRITICAL: All methods require Flask app context (get_db() dependency).
"""

import logging
import json
from datetime import datetime, date, time, timedelta
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


class AchievementRepository:
    """Repository for achievement data access.

    Enterprise-grade achievement tracking with proper separation of concerns:
    - AchievementRepository: Data access layer (CRUD operations)
    - AchievementService: Business logic layer (checking/awarding achievements)

    CRITICAL: All methods require Flask app context.
    """

    @staticmethod
    def get_achievement_type(code):
        """Get achievement type by code.

        Args:
            code: Achievement type code (e.g., 'first_perfect_hour')

        Returns:
            dict or None: Achievement type details
        """
        db = get_db()
        cursor = db.execute(
            """
            SELECT id, code, name, description, category, icon, points, tier, is_active
            FROM achievement_type
            WHERE code = ? AND is_active = 1
            """,
            (code,)
        )
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'code': row['code'],
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'icon': row['icon'],
                'points': row['points'],
                'tier': row['tier']
            }
        return None

    @staticmethod
    def get_all_achievement_types(category=None):
        """Get all active achievement types, optionally filtered by category.

        Args:
            category: Optional filter ('daily', 'weekly', 'milestone')

        Returns:
            list[dict]: Achievement type definitions
        """
        db = get_db()
        if category:
            cursor = db.execute(
                """
                SELECT id, code, name, description, category, icon, points, tier
                FROM achievement_type
                WHERE is_active = 1 AND category = ?
                ORDER BY points ASC
                """,
                (category,)
            )
        else:
            cursor = db.execute(
                """
                SELECT id, code, name, description, category, icon, points, tier
                FROM achievement_type
                WHERE is_active = 1
                ORDER BY category, points ASC
                """
            )

        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def has_earned_achievement(code, since_date=None):
        """Check if achievement has been earned (optionally since a date).

        Args:
            code: Achievement type code
            since_date: Optional date to check from (for daily achievements)

        Returns:
            bool: True if already earned
        """
        db = get_db()

        if since_date:
            cursor = db.execute(
                """
                SELECT ae.id FROM achievement_earned ae
                JOIN achievement_type at ON ae.achievement_type_id = at.id
                WHERE at.code = ? AND DATE(ae.earned_at) >= ?
                """,
                (code, since_date)
            )
        else:
            cursor = db.execute(
                """
                SELECT ae.id FROM achievement_earned ae
                JOIN achievement_type at ON ae.achievement_type_id = at.id
                WHERE at.code = ?
                """,
                (code,)
            )

        return cursor.fetchone() is not None

    @staticmethod
    def award_achievement(code, metadata=None):
        """Award an achievement to the user.

        Args:
            code: Achievement type code
            metadata: Optional context data (e.g., {'score': 85})

        Returns:
            dict: Awarded achievement details with earned_id

        Raises:
            ValueError: If achievement type not found
        """
        achievement_type = AchievementRepository.get_achievement_type(code)
        if not achievement_type:
            raise ValueError(f"Achievement type not found: {code}")

        db = get_db()
        metadata_json = json.dumps(metadata or {})

        cursor = db.execute(
            """
            INSERT INTO achievement_earned (achievement_type_id, earned_at, metadata, notified)
            VALUES (?, ?, ?, 0)
            """,
            (achievement_type['id'], datetime.now(), metadata_json)
        )
        db.commit()

        earned_id = cursor.lastrowid
        logger.info(f"Achievement awarded: {code} (id={earned_id})")

        return {
            'earned_id': earned_id,
            **achievement_type,
            'earned_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

    @staticmethod
    def get_earned_achievements(limit=50, include_notified=True):
        """Get list of earned achievements, most recent first.

        Args:
            limit: Maximum number to return
            include_notified: Include already-notified achievements

        Returns:
            list[dict]: Earned achievements with type details
        """
        db = get_db()

        notified_filter = "" if include_notified else "AND ae.notified = 0"

        cursor = db.execute(
            f"""
            SELECT ae.id as earned_id, ae.earned_at, ae.metadata, ae.notified,
                   at.code, at.name, at.description, at.category, at.icon, at.points, at.tier
            FROM achievement_earned ae
            JOIN achievement_type at ON ae.achievement_type_id = at.id
            WHERE at.is_active = 1 {notified_filter}
            ORDER BY ae.earned_at DESC
            LIMIT ?
            """,
            (limit,)
        )

        achievements = []
        for row in cursor.fetchall():
            achievements.append({
                'earned_id': row['earned_id'],
                'earned_at': row['earned_at'].isoformat() if isinstance(row['earned_at'], datetime) else row['earned_at'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'notified': bool(row['notified']),
                'code': row['code'],
                'name': row['name'],
                'description': row['description'],
                'category': row['category'],
                'icon': row['icon'],
                'points': row['points'],
                'tier': row['tier']
            })

        return achievements

    @staticmethod
    def get_unnotified_achievements():
        """Get achievements that haven't been notified to the user yet.

        Returns:
            list[dict]: Unnotified achievements
        """
        return AchievementRepository.get_earned_achievements(limit=10, include_notified=False)

    @staticmethod
    def mark_achievement_notified(earned_id):
        """Mark an achievement as notified.

        Args:
            earned_id: The earned achievement ID
        """
        db = get_db()
        db.execute(
            "UPDATE achievement_earned SET notified = 1 WHERE id = ?",
            (earned_id,)
        )
        db.commit()
        logger.debug(f"Achievement marked as notified: earned_id={earned_id}")

    @staticmethod
    def get_achievement_stats():
        """Get achievement statistics summary.

        Returns:
            dict: Stats including total_earned, total_points, by_category counts
        """
        db = get_db()

        # Total earned and points
        cursor = db.execute(
            """
            SELECT COUNT(*) as total, COALESCE(SUM(at.points), 0) as points
            FROM achievement_earned ae
            JOIN achievement_type at ON ae.achievement_type_id = at.id
            """
        )
        row = cursor.fetchone()
        total_earned = row['total']
        total_points = row['points']

        # Count by category
        cursor = db.execute(
            """
            SELECT at.category, COUNT(*) as count
            FROM achievement_earned ae
            JOIN achievement_type at ON ae.achievement_type_id = at.id
            GROUP BY at.category
            """
        )
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}

        # Total available achievements
        cursor = db.execute("SELECT COUNT(*) as total FROM achievement_type WHERE is_active = 1")
        total_available = cursor.fetchone()['total']

        return {
            'total_earned': total_earned,
            'total_available': total_available,
            'total_points': total_points,
            'by_category': by_category,
            'completion_percentage': round((total_earned / total_available * 100) if total_available > 0 else 0, 1)
        }

    @staticmethod
    def update_progress(code, progress_value, target_value, tracking_date=None):
        """Update or insert achievement progress tracking.

        Args:
            code: Achievement type code
            progress_value: Current progress value
            target_value: Target value to complete achievement
            tracking_date: Date to track (defaults to today)

        Returns:
            dict: Progress record
        """
        db = get_db()
        tracking_date = tracking_date or date.today()
        completed = progress_value >= target_value

        db.execute(
            """
            INSERT INTO achievement_progress (achievement_code, tracking_date, progress_value, target_value, completed, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(achievement_code, tracking_date) DO UPDATE SET
                progress_value = excluded.progress_value,
                completed = excluded.completed,
                updated_at = excluded.updated_at
            """,
            (code, tracking_date, progress_value, target_value, completed, datetime.now())
        )
        db.commit()

        return {
            'code': code,
            'tracking_date': tracking_date.isoformat(),
            'progress_value': progress_value,
            'target_value': target_value,
            'completed': completed,
            'percentage': min(100, round(progress_value / target_value * 100)) if target_value > 0 else 0
        }

    @staticmethod
    def get_progress(code, tracking_date=None):
        """Get achievement progress for a specific date.

        Args:
            code: Achievement type code
            tracking_date: Date to check (defaults to today)

        Returns:
            dict or None: Progress record if exists
        """
        db = get_db()
        tracking_date = tracking_date or date.today()

        cursor = db.execute(
            """
            SELECT achievement_code, tracking_date, progress_value, target_value, completed
            FROM achievement_progress
            WHERE achievement_code = ? AND tracking_date = ?
            """,
            (code, tracking_date)
        )
        row = cursor.fetchone()
        if row:
            return {
                'code': row['achievement_code'],
                'tracking_date': row['tracking_date'],
                'progress_value': row['progress_value'],
                'target_value': row['target_value'],
                'completed': bool(row['completed']),
                'percentage': min(100, round(row['progress_value'] / row['target_value'] * 100)) if row['target_value'] > 0 else 0
            }
        return None
