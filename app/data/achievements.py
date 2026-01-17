"""Achievement Service - Business logic for achievement tracking.

This module provides the business logic layer for checking and awarding achievements.
Separates concerns from AchievementRepository (data access) for enterprise-grade architecture.

Architecture:
- AchievementService: Business logic (this file)
- AchievementRepository: Data access (repository.py)
- Achievement checking runs after daily stats calculation

CRITICAL: All methods require Flask app context.

Achievement Validation Requirements:
- All daily achievements require MIN_MONITORING_TIME_DAILY (1 hour)
- Getting Started requires MIN_MONITORING_TIME_GETTING_STARTED (30 minutes)
- Streak achievements require MIN_MONITORING_TIME_PER_DAY per day (30 minutes)
"""

import logging
from datetime import datetime, date, timedelta
from app.data.repository import AchievementRepository
from app.data.analytics import PostureAnalytics

logger = logging.getLogger('deskpulse.achievements')


class AchievementService:
    """Service layer for achievement business logic.

    Responsibilities:
    - Check achievement criteria against current stats
    - Award achievements when criteria met
    - Prevent duplicate awards (idempotent)
    - Queue notifications for newly earned achievements

    IMPORTANT: Only achievements with implemented validation logic will be awarded.
    Achievements defined in schema but not implemented here will NOT be awarded.
    """

    # Minimum monitoring time thresholds (in seconds)
    MIN_MONITORING_TIME_DAILY = 3600      # 1 hour for daily achievements
    MIN_MONITORING_TIME_GETTING_STARTED = 1800  # 30 minutes for Getting Started
    MIN_MONITORING_TIME_PER_DAY = 1800    # 30 minutes per day for streak achievements

    # Time-of-day achievement thresholds
    MIN_GOOD_POSTURE_TIME_OF_DAY = 600    # 10 minutes good posture for early_bird/night_owl
    EARLY_BIRD_CUTOFF = '08:00:00'        # Before 8 AM
    NIGHT_OWL_START = '20:00:00'          # After 8 PM

    # Implemented achievements (only these will be checked/awarded)
    # Open Source Edition: 9 achievements for basic motivation
    IMPLEMENTED_ACHIEVEMENTS = {
        # Daily (require 1hr+ monitoring)
        'first_perfect_hour',   # 60 min total good posture
        'posture_champion',     # 80%+ score
        'early_bird',           # 10+ min good posture before 8 AM (+ 1hr daily monitoring)
        'night_owl',            # 10+ min good posture after 8 PM (+ 1hr daily monitoring)

        # Milestone (one-time)
        'getting_started',      # 30+ min monitoring
        'transformation',       # First 90%+ score (with 1hr monitoring)
        'habit_builder',        # 7 consecutive days (30min/day)

        # Weekly (checked on Sundays)
        'week_warrior',         # 70%+ average for 7 days
        'perfect_week',         # 5+ days with 80%+
    }

    # Premium achievements (available in closed-source edition):
    # - consistency_king: 4+ hours good posture
    # - posture_pro: 30 consecutive days
    # - century_club: 100 hours total good posture
    # - improvement_hero: 10+ point weekly improvement
    # - posture_champion_streak_30/90: 80%+ for 30/90 consecutive days
    # - century_club_gold/platinum: 500/1000 hours total
    # - perfect_month: 80%+ every day of a calendar month

    @staticmethod
    def check_and_award_achievements(stats=None, target_date=None):
        """Check all achievement criteria and award any newly earned.

        This is the main entry point, called after daily stats update.

        Args:
            stats: Pre-calculated daily stats (optional, will calculate if not provided)
            target_date: Date to check (defaults to today)

        Returns:
            list[dict]: Newly awarded achievements
        """
        target_date = target_date or date.today()
        newly_awarded = []

        try:
            # Get today's stats if not provided
            if stats is None:
                stats = PostureAnalytics.calculate_daily_stats(target_date)

            if not stats:
                logger.debug("No stats available for achievement check")
                return newly_awarded

            # Log current stats for debugging
            monitoring_time = stats.get('user_present_duration_seconds', 0)
            score = stats.get('posture_score', 0)
            logger.debug(f"Achievement check: monitoring={monitoring_time/60:.1f}min, score={score:.1f}%")

            # Check daily achievements (require 1hr+ monitoring)
            daily_awarded = AchievementService._check_daily_achievements(stats, target_date)
            newly_awarded.extend(daily_awarded)

            # Check milestone achievements
            milestone_awarded = AchievementService._check_milestone_achievements(stats, target_date)
            newly_awarded.extend(milestone_awarded)

            # Check weekly achievements (only on Sunday)
            if target_date.weekday() == 6:  # Sunday
                weekly_awarded = AchievementService._check_weekly_achievements(target_date)
                newly_awarded.extend(weekly_awarded)

            if newly_awarded:
                logger.info(f"Awarded {len(newly_awarded)} achievements: {[a['code'] for a in newly_awarded]}")

            return newly_awarded

        except Exception as e:
            logger.exception(f"Error checking achievements: {e}")
            return newly_awarded

    @staticmethod
    def _check_daily_achievements(stats, target_date):
        """Check daily achievement criteria.

        ALL daily achievements require minimum 1 hour of monitoring.

        Args:
            stats: Daily statistics dict
            target_date: Date being checked

        Returns:
            list[dict]: Newly awarded daily achievements
        """
        awarded = []

        # Get monitoring duration for validation
        monitoring_time = stats.get('user_present_duration_seconds', 0)
        score = stats.get('posture_score', 0)
        good_seconds = stats.get('good_duration_seconds', 0)

        # CRITICAL: Skip ALL daily achievements if insufficient monitoring time
        if monitoring_time < AchievementService.MIN_MONITORING_TIME_DAILY:
            logger.debug(
                f"Skipping daily achievements: {monitoring_time/60:.1f}min monitoring "
                f"(need {AchievementService.MIN_MONITORING_TIME_DAILY/60:.0f}min)"
            )
            return awarded

        logger.debug(f"Checking daily achievements: {monitoring_time/60:.1f}min monitoring, {score:.1f}% score")

        # First Perfect Hour: 60+ minutes TOTAL of good posture
        good_minutes = good_seconds / 60
        if good_minutes >= 60:
            achievement = AchievementService._try_award(
                'first_perfect_hour',
                since_date=target_date,
                metadata={
                    'good_minutes': round(good_minutes),
                    'monitoring_minutes': round(monitoring_time / 60)
                }
            )
            if achievement:
                awarded.append(achievement)

        # Posture Champion: 80%+ score
        if score >= 80:
            achievement = AchievementService._try_award(
                'posture_champion',
                since_date=target_date,
                metadata={
                    'score': round(score),
                    'monitoring_minutes': round(monitoring_time / 60)
                }
            )
            if achievement:
                awarded.append(achievement)

        # Early Bird: 10+ minutes good posture before 8 AM
        early_good_seconds = AchievementService._get_good_posture_in_time_window(
            target_date,
            end_time=AchievementService.EARLY_BIRD_CUTOFF
        )
        if early_good_seconds >= AchievementService.MIN_GOOD_POSTURE_TIME_OF_DAY:
            achievement = AchievementService._try_award(
                'early_bird',
                since_date=target_date,
                metadata={
                    'early_good_minutes': round(early_good_seconds / 60, 1),
                    'monitoring_minutes': round(monitoring_time / 60)
                }
            )
            if achievement:
                awarded.append(achievement)

        # Night Owl: 10+ minutes good posture after 8 PM
        night_good_seconds = AchievementService._get_good_posture_in_time_window(
            target_date,
            start_time=AchievementService.NIGHT_OWL_START
        )
        if night_good_seconds >= AchievementService.MIN_GOOD_POSTURE_TIME_OF_DAY:
            achievement = AchievementService._try_award(
                'night_owl',
                since_date=target_date,
                metadata={
                    'night_good_minutes': round(night_good_seconds / 60, 1),
                    'monitoring_minutes': round(monitoring_time / 60)
                }
            )
            if achievement:
                awarded.append(achievement)

        return awarded

    @staticmethod
    def _check_milestone_achievements(stats, target_date):
        """Check milestone (one-time) achievement criteria.

        Args:
            stats: Daily statistics dict
            target_date: Date being checked

        Returns:
            list[dict]: Newly awarded milestone achievements
        """
        awarded = []

        # Get monitoring duration for validation
        monitoring_time = stats.get('user_present_duration_seconds', 0)
        score = stats.get('posture_score', 0)

        # Getting Started: First session with 30+ minutes of monitoring
        if not AchievementRepository.has_earned_achievement('getting_started'):
            if monitoring_time >= AchievementService.MIN_MONITORING_TIME_GETTING_STARTED:
                achievement = AchievementService._try_award(
                    'getting_started',
                    metadata={
                        'monitoring_minutes': round(monitoring_time / 60),
                        'date': target_date.isoformat()
                    }
                )
                if achievement:
                    awarded.append(achievement)
            else:
                logger.debug(
                    f"Getting Started not earned: {monitoring_time/60:.1f}min "
                    f"(need {AchievementService.MIN_MONITORING_TIME_GETTING_STARTED/60:.0f}min)"
                )

        # Transformation: First 90%+ score (requires 1hr+ monitoring)
        if not AchievementRepository.has_earned_achievement('transformation'):
            if score >= 90:
                if monitoring_time >= AchievementService.MIN_MONITORING_TIME_DAILY:
                    achievement = AchievementService._try_award(
                        'transformation',
                        metadata={
                            'score': round(score),
                            'monitoring_minutes': round(monitoring_time / 60),
                            'date': target_date.isoformat()
                        }
                    )
                    if achievement:
                        awarded.append(achievement)
                else:
                    logger.debug(
                        f"Transformation not earned: {monitoring_time/60:.1f}min "
                        f"(need {AchievementService.MIN_MONITORING_TIME_DAILY/60:.0f}min)"
                    )

        # Habit Builder: 7 consecutive days with meaningful tracking
        consecutive = AchievementService._get_consecutive_tracking_days(target_date)
        logger.debug(f"Consecutive tracking days: {consecutive}")

        if consecutive >= 7 and not AchievementRepository.has_earned_achievement('habit_builder'):
            achievement = AchievementService._try_award(
                'habit_builder',
                metadata={'consecutive_days': consecutive}
            )
            if achievement:
                awarded.append(achievement)

        return awarded

    @staticmethod
    def _check_weekly_achievements(target_date):
        """Check weekly achievement criteria.

        Only called on Sundays. Requires each day in the week to have
        meaningful monitoring time.

        Args:
            target_date: End of week date (Sunday)

        Returns:
            list[dict]: Newly awarded weekly achievements
        """
        awarded = []

        try:
            # Get 7-day history
            history = PostureAnalytics.get_7_day_history()

            if len(history) < 7:
                logger.debug(f"Weekly achievements skipped: only {len(history)} days of history")
                return awarded

            # Validate each day has meaningful monitoring (30+ minutes)
            valid_days = []
            for day in history:
                day_monitoring = day.get('user_present_duration_seconds', 0)
                if day_monitoring >= AchievementService.MIN_MONITORING_TIME_PER_DAY:
                    valid_days.append(day)

            if len(valid_days) < 7:
                logger.debug(
                    f"Weekly achievements skipped: only {len(valid_days)}/7 days "
                    f"with {AchievementService.MIN_MONITORING_TIME_PER_DAY/60:.0f}+ min monitoring"
                )
                return awarded

            # Week Warrior: 70%+ average for 7 valid days
            avg_score = sum(d.get('posture_score', 0) for d in valid_days) / len(valid_days)
            if avg_score >= 70:
                achievement = AchievementService._try_award(
                    'week_warrior',
                    since_date=target_date - timedelta(days=6),
                    metadata={
                        'average_score': round(avg_score, 1),
                        'valid_days': len(valid_days)
                    }
                )
                if achievement:
                    awarded.append(achievement)

            # Perfect Week: 5+ days with 80%+ score
            days_above_80 = sum(1 for d in valid_days if d.get('posture_score', 0) >= 80)
            if days_above_80 >= 5:
                achievement = AchievementService._try_award(
                    'perfect_week',
                    since_date=target_date - timedelta(days=6),
                    metadata={'days_above_80': days_above_80}
                )
                if achievement:
                    awarded.append(achievement)

        except Exception as e:
            logger.warning(f"Error checking weekly achievements: {e}")

        return awarded

    @staticmethod
    def _try_award(code, since_date=None, metadata=None):
        """Try to award an achievement if not already earned.

        Args:
            code: Achievement type code
            since_date: For daily/weekly, check if earned since this date
            metadata: Context data for the achievement

        Returns:
            dict or None: Achievement details if awarded, None if already earned
        """
        # Only award implemented achievements
        if code not in AchievementService.IMPLEMENTED_ACHIEVEMENTS:
            logger.warning(f"Attempted to award unimplemented achievement: {code}")
            return None

        try:
            # Check if already earned
            if AchievementRepository.has_earned_achievement(code, since_date=since_date):
                logger.debug(f"Achievement already earned: {code}")
                return None

            # Award achievement
            achievement = AchievementRepository.award_achievement(code, metadata)
            logger.info(f"Achievement awarded: {code} with metadata: {metadata}")
            return achievement

        except Exception as e:
            logger.error(f"Error awarding achievement {code}: {e}")
            return None

    @staticmethod
    def _get_consecutive_tracking_days(end_date):
        """Count consecutive days with meaningful tracking data ending at end_date.

        A day counts as a "tracking day" only if it has at least
        MIN_MONITORING_TIME_PER_DAY seconds of monitoring.

        Args:
            end_date: Date to count backwards from

        Returns:
            int: Number of consecutive days with meaningful tracking
        """
        from app.data.database import get_db

        db = get_db()
        consecutive = 0
        check_date = end_date

        # Check up to 60 days back
        for _ in range(60):
            # Get total monitoring time for this day
            cursor = db.execute(
                """
                SELECT
                    COUNT(*) as event_count,
                    MIN(timestamp) as first_event,
                    MAX(timestamp) as last_event
                FROM posture_event
                WHERE DATE(timestamp) = ? AND user_present = 1
                """,
                (check_date,)
            )
            row = cursor.fetchone()

            event_count = row['event_count'] or 0

            # Estimate monitoring time: ~1 event per second when user present
            # Require at least 30 minutes (1800 events) of monitoring
            min_events_for_day = AchievementService.MIN_MONITORING_TIME_PER_DAY  # 1800 events ≈ 30 min

            if event_count >= min_events_for_day:
                consecutive += 1
                check_date = check_date - timedelta(days=1)
            else:
                logger.debug(
                    f"Day {check_date}: {event_count} events "
                    f"(need {min_events_for_day} for tracking day)"
                )
                break

        return consecutive

    @staticmethod
    def _get_good_posture_in_time_window(target_date, start_time=None, end_time=None):
        """Get count of good posture events within a time window on a specific date.

        Since posture_event stores ~1 event per second, the count approximates
        seconds of good posture in that time window.

        Args:
            target_date: Date to check
            start_time: Start of window as 'HH:MM:SS' string (inclusive), None for midnight
            end_time: End of window as 'HH:MM:SS' string (exclusive), None for end of day

        Returns:
            int: Count of good posture events (approximately seconds) in the window
        """
        from app.data.database import get_db

        db = get_db()

        # Build query based on time window
        if start_time and end_time:
            # Both bounds specified
            cursor = db.execute(
                """
                SELECT COUNT(*) as good_count
                FROM posture_event
                WHERE DATE(timestamp) = ?
                  AND TIME(timestamp) >= ?
                  AND TIME(timestamp) < ?
                  AND posture_state = 'good'
                  AND user_present = 1
                """,
                (target_date, start_time, end_time)
            )
        elif start_time:
            # Only start time (e.g., night_owl: after 8 PM)
            cursor = db.execute(
                """
                SELECT COUNT(*) as good_count
                FROM posture_event
                WHERE DATE(timestamp) = ?
                  AND TIME(timestamp) >= ?
                  AND posture_state = 'good'
                  AND user_present = 1
                """,
                (target_date, start_time)
            )
        elif end_time:
            # Only end time (e.g., early_bird: before 8 AM)
            cursor = db.execute(
                """
                SELECT COUNT(*) as good_count
                FROM posture_event
                WHERE DATE(timestamp) = ?
                  AND TIME(timestamp) < ?
                  AND posture_state = 'good'
                  AND user_present = 1
                """,
                (target_date, end_time)
            )
        else:
            # No bounds - count all good posture for the day
            cursor = db.execute(
                """
                SELECT COUNT(*) as good_count
                FROM posture_event
                WHERE DATE(timestamp) = ?
                  AND posture_state = 'good'
                  AND user_present = 1
                """,
                (target_date,)
            )

        row = cursor.fetchone()
        good_count = row['good_count'] or 0

        logger.debug(
            f"Good posture in window (date={target_date}, start={start_time}, end={end_time}): "
            f"{good_count} events (~{good_count/60:.1f} min)"
        )

        return good_count

    @staticmethod
    def get_achievement_summary():
        """Get complete achievement summary for dashboard display.

        Returns:
            dict: Summary with earned, available, and progress data
        """
        try:
            stats = AchievementRepository.get_achievement_stats()
            earned = AchievementRepository.get_earned_achievements(limit=20)
            all_types = AchievementRepository.get_all_achievement_types()

            # Create a set of earned achievement codes
            earned_codes = {a['code'] for a in earned}

            # Only show implemented achievements as available
            available = []
            for atype in all_types:
                if atype['code'] in AchievementService.IMPLEMENTED_ACHIEVEMENTS:
                    available.append({
                        **atype,
                        'earned': atype['code'] in earned_codes
                    })

            # Update stats to reflect only implemented achievements
            stats['total_available'] = len(AchievementService.IMPLEMENTED_ACHIEVEMENTS)

            return {
                'stats': stats,
                'earned': earned,
                'available': available,
                'recent': earned[:5]
            }

        except Exception as e:
            logger.exception(f"Error getting achievement summary: {e}")
            return {
                'stats': {'total_earned': 0, 'total_available': 0, 'total_points': 0},
                'earned': [],
                'available': [],
                'recent': []
            }

    @staticmethod
    def get_unnotified_achievements():
        """Get achievements that need to be notified to the user.

        Returns:
            list[dict]: Achievements pending notification
        """
        return AchievementRepository.get_unnotified_achievements()

    @staticmethod
    def mark_notified(earned_id):
        """Mark an achievement as notified.

        Args:
            earned_id: The earned achievement ID
        """
        AchievementRepository.mark_achievement_notified(earned_id)
