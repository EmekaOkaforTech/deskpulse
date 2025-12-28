"""Analytics engine for posture statistics and trends.

This module transforms raw posture events into meaningful daily statistics,
including posture scores, duration tracking, and historical trends.

CRITICAL: All methods require Flask app context (PostureEventRepository dependency).

Enterprise-Grade Validation:
- Type hints for static analysis (MyPy compatible)
- Runtime input validation with TypeError/ValueError
- Defensive programming against edge cases (negative durations, invalid dates)
"""

import logging
from datetime import datetime, timedelta, date, time
from typing import Dict, List, Any, Union
from app.data.repository import PostureEventRepository

logger = logging.getLogger('deskpulse.analytics')


class PostureAnalytics:
    """Calculate posture statistics and trends from event data.

    CRITICAL: All methods require Flask app context.
    - API Routes: Automatically have context via Flask request
    - Tests: Must use app.app_context() or app_context fixture
    """

    @staticmethod
    def calculate_daily_stats(target_date: date) -> Dict[str, Any]:
        """Calculate daily posture statistics from real event data.

        Args:
            target_date: date object for calculation (NOT datetime)

        Returns:
            dict: {
                'date': date,                           # datetime.date object
                'good_duration_seconds': int,           # Time in good posture
                'bad_duration_seconds': int,            # Time in bad posture
                'user_present_duration_seconds': int,   # Total active time
                'posture_score': float,                 # 0-100 percentage
                'total_events': int                     # Event count
            }

        Algorithm:
            1. Load all events for target_date via PostureEventRepository
            2. Calculate duration for each state by time between consecutive events
            3. Handle last event: cap at 10 minutes or end of day (whichever is sooner)
            4. Calculate posture_score = (good_duration / total_duration) * 100
            5. Return statistics dict

        Edge Cases:
            - No events: Return all zeros with date
            - Single event: Duration capped at 10 minutes
            - Events spanning midnight: Only count time within target_date
            - User absent periods: Not counted in duration calculations
            - Zero duration: Posture score = 0.0 (avoid division by zero)
            - Negative remaining_duration: Clamped to 0 (clock skew protection)

        Raises:
            TypeError: If target_date is not a date object
            Exception: Database errors (logged and re-raised for API error handling)
        """
        # Enterprise-grade input validation
        if not isinstance(target_date, date):
            raise TypeError(
                f"target_date must be datetime.date object, got {type(target_date).__name__}. "
                f"If you have a datetime, call .date() first."
            )

        # Prevent datetime objects (common mistake)
        if isinstance(target_date, datetime):
            raise TypeError(
                f"target_date must be date object, not datetime. Call .date() to convert."
            )

        try:
            events = PostureEventRepository.get_events_for_date(target_date)
        except Exception as e:
            logger.error(
                f"Database error retrieving events for {target_date}: {e}",
                exc_info=True
            )
            raise  # Re-raise for API layer to handle

        # Edge case: No events
        if not events:
            return {
                'date': target_date,
                'good_duration_seconds': 0,
                'bad_duration_seconds': 0,
                'user_present_duration_seconds': 0,
                'posture_score': 0.0,
                'total_events': 0
            }

        # Calculate duration for each posture state
        good_duration = 0
        bad_duration = 0

        # Process consecutive events
        for i in range(len(events) - 1):
            current_event = events[i]
            next_event = events[i + 1]

            # Calculate time between events
            # Note: Repository returns timestamp as ISO 8601 string from database
            # fromisoformat() handles both string and datetime objects
            current_ts = current_event['timestamp']
            next_ts = next_event['timestamp']

            # Convert to datetime if string (defensive programming)
            if isinstance(current_ts, str):
                current_ts = datetime.fromisoformat(current_ts)
            if isinstance(next_ts, str):
                next_ts = datetime.fromisoformat(next_ts)

            duration = (next_ts - current_ts).total_seconds()

            # Accumulate based on current state
            if current_event['posture_state'] == 'good':
                good_duration += duration
            elif current_event['posture_state'] == 'bad':
                bad_duration += duration

        # Handle last event (cap at 10 minutes or end of day, whichever is sooner)
        last_event = events[-1]
        last_timestamp = last_event['timestamp']
        if isinstance(last_timestamp, str):
            last_timestamp = datetime.fromisoformat(last_timestamp)

        end_of_day = datetime.combine(target_date, time.max)  # 23:59:59.999999

        # CRITICAL: Protect against negative durations from clock skew or timezone issues
        # If last event is after EOD (shouldn't happen, but defensive programming),
        # max(0, ...) ensures we never add negative duration
        remaining_duration = max(0, min(
            (end_of_day - last_timestamp).total_seconds(),
            600  # Cap at 10 minutes (prevents overnight inflation)
        ))

        if last_event['posture_state'] == 'good':
            good_duration += remaining_duration
        elif last_event['posture_state'] == 'bad':
            bad_duration += remaining_duration

        # Calculate total user-present duration
        user_present_duration = good_duration + bad_duration

        # Calculate posture score (percentage of time in good posture)
        # Edge case: Zero division safety
        if user_present_duration > 0:
            posture_score = (good_duration / user_present_duration) * 100
        else:
            posture_score = 0.0

        stats = {
            'date': target_date,
            'good_duration_seconds': int(good_duration),
            'bad_duration_seconds': int(bad_duration),
            'user_present_duration_seconds': int(user_present_duration),
            'posture_score': round(posture_score, 1),
            'total_events': len(events)
        }

        logger.info(
            f"Daily stats for {target_date}: score={stats['posture_score']}%, "
            f"good={format_duration(good_duration)}, bad={format_duration(bad_duration)}"
        )

        return stats

    @staticmethod
    def get_7_day_history() -> List[Dict[str, Any]]:
        """Get posture statistics for the last 7 days (including today).

        Returns:
            list: List of daily stats dicts, ordered by date (oldest first)
                  Format: [day_6_ago, day_5_ago, ..., yesterday, today]

        Implementation:
            1. Calculate today's date
            2. Loop from 6 days ago to today (7 total days)
            3. Call calculate_daily_stats() for each date
            4. Append to results list
            5. Return list ordered chronologically (oldest first)

        Performance Note:
            Makes 7 separate database queries (one per day).
            Acceptable for MVP scale, but future optimization could use
            single query with date range + Python grouping.
        """
        history = []
        today = date.today()

        # Loop from 6 days ago to today (7 total days)
        for days_ago in range(6, -1, -1):  # 6, 5, 4, 3, 2, 1, 0
            target_date = today - timedelta(days=days_ago)
            daily_stats = PostureAnalytics.calculate_daily_stats(target_date)
            history.append(daily_stats)

        logger.debug(f"Retrieved 7-day history: {len(history)} days")
        return history


def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds (int or float)

    Returns:
        str: Formatted duration:
            - "2h 15m" for hours+minutes
            - "45m" for minutes only
            - "0m" for zero or negative values

    Examples:
        format_duration(7890) -> "2h 11m"
        format_duration(300) -> "5m"
        format_duration(0) -> "0m"
        format_duration(-100) -> "0m"
    """
    # Handle zero and negative durations (edge case)
    if seconds <= 0:
        return "0m"

    # Calculate hours and minutes
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)

    # Format based on duration
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
