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
from typing import Dict, List, Any, Union, Optional
from app.data.repository import PostureEventRepository

logger = logging.getLogger('deskpulse.analytics')


class PostureAnalytics:
    """Calculate posture statistics and trends from event data.

    CRITICAL: All methods require Flask app context.
    - API Routes: Automatically have context via Flask request
    - Tests: Must use app.app_context() or app_context fixture
    """

    @staticmethod
    def calculate_daily_stats(target_date: date, pause_timestamp=None) -> Dict[str, Any]:
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

            # CRITICAL: Skip duration if current event is a pause marker
            # The time between pause marker and resume marker is paused period
            # and should NOT be counted in posture duration
            current_metadata = current_event.get('metadata', {})
            if current_metadata.get('monitoring_paused'):
                logger.debug(f"Skipping paused period: event {i} is pause marker")
                continue

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

        # Handle last event (cap at 10 minutes or end boundary, whichever is sooner)
        last_event = events[-1]
        last_metadata = last_event.get('metadata', {})

        # CRITICAL: If last event is a pause marker, don't add remaining duration
        # Monitoring is paused, so no time should accumulate from pause marker
        if last_metadata.get('monitoring_paused'):
            logger.debug("Last event is pause marker - no remaining duration added")
            remaining_duration = 0
        else:
            last_timestamp = last_event['timestamp']
            if isinstance(last_timestamp, str):
                last_timestamp = datetime.fromisoformat(last_timestamp)

            # CRITICAL FIX: For today, use current time as endpoint (live stats)
            # BUT if monitoring is paused, use pause_timestamp to prevent phantom accumulation
            # For past dates, use end of day
            if target_date == date.today():
                if pause_timestamp is not None:
                    # Monitoring is paused - use pause time, NOT current time
                    # This prevents the last event from accumulating duration while paused
                    end_boundary = pause_timestamp
                else:
                    # Monitoring active - use current time for live stats
                    end_boundary = datetime.now()
            else:
                end_boundary = datetime.combine(target_date, time.max)  # 23:59:59.999999

            # CRITICAL: Protect against negative durations from clock skew or timezone issues
            # If last event is after end_boundary (shouldn't happen, but defensive programming),
            # max(0, ...) ensures we never add negative duration
            remaining_duration = max(0, min(
                (end_boundary - last_timestamp).total_seconds(),
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
    def get_7_day_history(pause_timestamp=None) -> List[Dict[str, Any]]:
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
            # CRITICAL: Pass pause_timestamp ONLY for today (not historical dates)
            if target_date == today:
                daily_stats = PostureAnalytics.calculate_daily_stats(target_date, pause_timestamp=pause_timestamp)
            else:
                daily_stats = PostureAnalytics.calculate_daily_stats(target_date)
            history.append(daily_stats)

        logger.debug(f"Retrieved 7-day history: {len(history)} days")
        return history

    @staticmethod
    def calculate_trend(history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate posture improvement trend from historical data.

        Args:
            history: List of daily stats dicts from get_7_day_history()
                     Format: [{date, good_duration_seconds, bad_duration_seconds,
                              posture_score, total_events}, ...]

        Returns:
            dict: {
                'trend': str,                    # 'improving', 'stable', 'declining', 'insufficient_data'
                'average_score': float,          # Mean score across all days
                'score_change': float,           # Points change from first to last day
                'best_day': dict,                # Daily stats dict for highest score day
                'improvement_message': str       # User-facing progress message (UX: Progress framing)
            }

        Trend Classification:
            - improving: score_change > 10 points (meaningful improvement)
            - declining: score_change < -10 points (meaningful decline)
            - stable: -10 ≤ score_change ≤ 10 (consistent performance)
            - insufficient_data: len(history) < 2 (need 2+ days for comparison)

        Edge Cases:
            - Empty history → insufficient_data trend
            - Single day → insufficient_data trend
            - All zero scores → stable trend with "Keep monitoring" message

        Raises:
            TypeError: If history is not a list or contains non-dict elements
            ValueError: If history dicts are missing required keys
        """
        # Enterprise-grade input validation (Code Review Fix #1)
        if not isinstance(history, list):
            raise TypeError(f"history must be a list, got {type(history).__name__}")

        for i, day in enumerate(history):
            if not isinstance(day, dict):
                raise TypeError(f"history[{i}] must be dict, got {type(day).__name__}")
            if 'posture_score' not in day:
                raise ValueError(f"history[{i}] missing required 'posture_score' key")

        # Insufficient data check
        if len(history) < 2:
            return {
                'trend': 'insufficient_data',
                'average_score': 0.0,
                'score_change': 0.0,
                'best_day': None,
                'improvement_message': 'Keep monitoring to see your progress!'
            }

        # Calculate average score across all days
        total_score = sum(day['posture_score'] for day in history)
        average_score = total_score / len(history)

        # Calculate score change (first day → last day)
        first_score = history[0]['posture_score']
        last_score = history[-1]['posture_score']
        score_change = last_score - first_score

        # Defensive programming: Handle NaN/Infinity edge cases (Code Review Fix #9)
        import math
        if not math.isfinite(average_score) or not math.isfinite(score_change):
            logger.error(f"Non-finite values detected: avg={average_score}, change={score_change}")
            return {
                'trend': 'insufficient_data',
                'average_score': 0.0,
                'score_change': 0.0,
                'best_day': None,
                'improvement_message': 'Unable to calculate trend due to data quality issues.'
            }

        # Classify trend (>10 points threshold to ignore noise)
        if score_change > 10:
            trend = 'improving'
        elif score_change < -10:
            trend = 'declining'
        else:
            trend = 'stable'

        # Find best day (highest score)
        best_day = max(history, key=lambda d: d['posture_score'])

        # Generate improvement message (UX Design: Progress framing)
        if trend == 'improving':
            improvement_message = f"You've improved {abs(score_change):.1f} points this week! Keep it up!"
        elif trend == 'declining':
            improvement_message = f"Your score has decreased {abs(score_change):.1f} points. Try focusing on posture during work sessions."
        else:  # stable
            improvement_message = f"Your posture is stable at {average_score:.1f}%. Consistency is key!"

        logger.info(
            f"Trend calculated: {trend}, change={score_change:.1f}, avg={average_score:.1f}"
        )

        return {
            'trend': trend,
            'average_score': round(average_score, 1),
            'score_change': round(score_change, 1),
            'best_day': best_day,
            'improvement_message': improvement_message
        }

    @staticmethod
    def generate_daily_summary(target_date: Optional[date] = None, pause_timestamp=None) -> str:
        """Generate end-of-day text summary report.

        Creates human-readable summary with progress framing, day-over-day
        comparison, and motivational messaging based on performance.

        Args:
            target_date: Date for summary (defaults to today)

        Returns:
            str: Multi-line text summary with emoji, scores, and motivation

        Example Output:
            📊 DeskPulse Daily Summary - Friday, December 28

            Posture Score: 68.5%
            Good Posture: 5h 23m
            Bad Posture: 2h 31m

            ✨ Improvement: +12.3 points from yesterday!

            👍 Good job! Keep building on this progress.

        Algorithm:
            1. Get today's stats via calculate_daily_stats()
            2. Get yesterday's stats for comparison
            3. Calculate score_change = today - yesterday
            4. Format durations using format_duration()
            5. Apply progress framing (UX Design):
               - >+5 points: "✨ Improvement: +X points from yesterday!"
               - <-5 points: "📉 Change: -X points from yesterday"
               - Otherwise: "→ Consistent: Similar to yesterday"
            6. Add motivational message based on score tier:
               - ≥75%: "🎉 Excellent work! Your posture was great today."
               - ≥50%: "👍 Good job! Keep building on this progress."
               - ≥30%: "💪 Room for improvement. Focus on posture during work sessions tomorrow."
               - <30%: "🔔 Let's work on better posture tomorrow. You've got this!"
            7. Return formatted text

        Edge Cases:
            - No data for today → Score 0%, message: "No posture data today"
            - No data for yesterday → Compare to 0, show improvement
            - Zero duration → Posture score 0%, message: "No active monitoring today"

        Enterprise Features:
            - Type hints for static analysis
            - Defensive defaults (today if no target_date)
            - Logging for audit trail
            - Reuses existing calculate_daily_stats() (NO duplication)

        Story 4.6: End-of-Day Summary Report
        """
        from datetime import timedelta

        # Default to today if no date specified
        if target_date is None:
            target_date = date.today()

        # Validate input type (enterprise-grade defensive programming)
        if not isinstance(target_date, date):
            raise TypeError(
                f"target_date must be datetime.date object, got {type(target_date).__name__}"
            )

        # Prevent datetime objects (common mistake)
        if isinstance(target_date, datetime):
            raise TypeError(
                "target_date must be date object, not datetime. Call .date() to convert."
            )

        # Get today's statistics (REAL backend connection via Story 4.2)
        # CRITICAL: Pass pause_timestamp for today, not for yesterday
        stats = PostureAnalytics.calculate_daily_stats(target_date, pause_timestamp=pause_timestamp)

        # Get yesterday's statistics for comparison (historical, no pause_timestamp)
        yesterday = target_date - timedelta(days=1)
        yesterday_stats = PostureAnalytics.calculate_daily_stats(yesterday)

        # Format durations
        good_time = format_duration(stats['good_duration_seconds'])
        bad_time = format_duration(stats['bad_duration_seconds'])
        score = stats['posture_score']

        # Calculate day-over-day change
        score_change = score - yesterday_stats['posture_score']

        # Build summary (UX Design: Progress framing)
        summary_lines = []
        summary_lines.append(f"📊 DeskPulse Daily Summary - {target_date.strftime('%A, %B %d')}")
        summary_lines.append("")

        # Handle no-data edge case
        if stats['total_events'] == 0:
            summary_lines.append("No posture data collected today.")
            summary_lines.append("")
            summary_lines.append("🔔 Make sure monitoring is running tomorrow!")
        else:
            summary_lines.append(f"Posture Score: {score:.1f}%")
            summary_lines.append(f"Good Posture: {good_time}")
            summary_lines.append(f"Bad Posture: {bad_time}")
            summary_lines.append("")

            # Progress framing (threshold: 5 points to ignore daily noise)
            if score_change > 5:
                summary_lines.append(f"✨ Improvement: +{score_change:.1f} points from yesterday!")
            elif score_change < -5:
                summary_lines.append(f"📉 Change: {score_change:.1f} points from yesterday")
            else:
                summary_lines.append(f"→ Consistent: Similar to yesterday ({score_change:+.1f} points)")

            summary_lines.append("")

            # Motivational message based on score (UX Design: Positive reinforcement)
            if score >= 75:
                summary_lines.append("🎉 Excellent work! Your posture was great today.")
            elif score >= 50:
                summary_lines.append("👍 Good job! Keep building on this progress.")
            elif score >= 30:
                summary_lines.append("💪 Room for improvement. Focus on posture during work sessions tomorrow.")
            else:
                summary_lines.append("🔔 Let's work on better posture tomorrow. You've got this!")

        summary = "\n".join(summary_lines)

        logger.info(
            f"Daily summary generated for {target_date}: score={score:.1f}%, "
            f"change={score_change:+.1f}, events={stats['total_events']}"
        )

        return summary


def format_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds (int or float)

    Returns:
        str: Formatted duration:
            - "2h 15m" for hours+minutes
            - "45m" for minutes only
            - "11s" for seconds only (< 1 minute)
            - "0s" for zero or negative values

    Examples:
        format_duration(7890) -> "2h 11m"
        format_duration(300) -> "5m"
        format_duration(11) -> "11s"
        format_duration(0) -> "0s"
        format_duration(-100) -> "0s"
    """
    # Handle zero and negative durations (edge case)
    if seconds <= 0:
        return "0s"

    # Calculate hours, minutes, and seconds
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    # Format based on duration
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        # Less than 1 minute - show seconds
        return f"{secs}s"
