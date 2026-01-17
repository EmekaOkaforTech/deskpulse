"""Achievement Service - Business logic for achievement tracking.

This module provides the business logic layer for checking and awarding achievements.
Separates concerns from AchievementRepository (data access) for enterprise-grade architecture.

Architecture:
- AchievementService: Business logic (this file)
- AchievementRepository: Data access (repository.py)
- Achievement checking runs after daily stats calculation

CRITICAL: All methods require Flask app context.
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
    """

    # Achievement criteria definitions (business rules)
    ACHIEVEMENT_CRITERIA = {
        # Daily achievements - reset each day
        'first_perfect_hour': {
            'check': 'good_duration_minutes',
            'threshold': 60,
            'daily': True,
            'description': '60+ consecutive minutes of good posture'
        },
        'posture_champion': {
            'check': 'posture_score',
            'threshold': 80,
            'daily': True,
            'description': '80%+ daily posture score'
        },
        'consistency_king': {
            'check': 'good_duration_hours',
            'threshold': 4,
            'daily': True,
            'description': '4+ hours of good posture in one day'
        },
        'early_bird': {
            'check': 'early_morning_good',
            'threshold': 1,
            'daily': True,
            'description': 'Good posture before 8 AM'
        },
        'night_owl': {
            'check': 'evening_good',
            'threshold': 1,
            'daily': True,
            'description': 'Good posture after 8 PM'
        },

        # Milestone achievements - one-time
        'getting_started': {
            'check': 'total_monitoring_days',
            'threshold': 1,
            'daily': False,
            'description': 'Complete first day of monitoring'
        },
        'habit_builder': {
            'check': 'consecutive_days',
            'threshold': 7,
            'daily': False,
            'description': '7 consecutive days of tracking'
        },
        'posture_pro': {
            'check': 'consecutive_days',
            'threshold': 30,
            'daily': False,
            'description': '30 consecutive days of tracking'
        },
        'transformation': {
            'check': 'peak_score',
            'threshold': 90,
            'daily': False,
            'description': 'First time achieving 90%+ score'
        },
        'century_club': {
            'check': 'total_good_hours',
            'threshold': 100,
            'daily': False,
            'description': '100 hours of good posture accumulated'
        },

        # Weekly achievements - reset each week
        'week_warrior': {
            'check': 'weekly_average',
            'threshold': 70,
            'weekly': True,
            'description': '70%+ average for 7 days'
        },
        'improvement_hero': {
            'check': 'weekly_improvement',
            'threshold': 10,
            'weekly': True,
            'description': '10+ point improvement week over week'
        },
        'perfect_week': {
            'check': 'days_above_80',
            'threshold': 5,
            'weekly': True,
            'description': '5+ days with 80%+ score in a week'
        }
    }

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

            # Check daily achievements
            daily_awarded = AchievementService._check_daily_achievements(stats, target_date)
            newly_awarded.extend(daily_awarded)

            # Check milestone achievements
            milestone_awarded = AchievementService._check_milestone_achievements(stats, target_date)
            newly_awarded.extend(milestone_awarded)

            # Check weekly achievements (only on Sunday or when week completes)
            if target_date.weekday() == 6:  # Sunday
                weekly_awarded = AchievementService._check_weekly_achievements(target_date)
                newly_awarded.extend(weekly_awarded)

            if newly_awarded:
                logger.info(f"Awarded {len(newly_awarded)} achievements: {[a['code'] for a in newly_awarded]}")

            return newly_awarded

        except Exception as e:
            logger.exception(f"Error checking achievements: {e}")
            return newly_awarded

    # Minimum monitoring time required for daily achievements (in seconds)
    MIN_MONITORING_TIME_DAILY = 3600  # 1 hour minimum monitoring for daily achievements
    MIN_MONITORING_TIME_GETTING_STARTED = 1800  # 30 minutes for "Getting Started"

    @staticmethod
    def _check_daily_achievements(stats, target_date):
        """Check daily achievement criteria.

        Args:
            stats: Daily statistics dict
            target_date: Date being checked

        Returns:
            list[dict]: Newly awarded daily achievements
        """
        awarded = []

        # Get monitoring duration for validation
        monitoring_time = stats.get('user_present_duration_seconds', 0)

        # Skip daily achievements if insufficient monitoring time
        if monitoring_time < AchievementService.MIN_MONITORING_TIME_DAILY:
            logger.debug(f"Skipping daily achievements: only {monitoring_time/60:.1f} min monitoring (need 60 min)")
            return awarded

        # First Perfect Hour: 60+ minutes TOTAL of good posture (not consecutive)
        good_minutes = stats.get('good_duration_seconds', 0) / 60
        if good_minutes >= 60:
            achievement = AchievementService._try_award(
                'first_perfect_hour',
                since_date=target_date,
                metadata={'good_minutes': round(good_minutes), 'monitoring_minutes': round(monitoring_time/60)}
            )
            if achievement:
                awarded.append(achievement)

        # Posture Champion: 80%+ score (requires 1+ hour monitoring)
        score = stats.get('posture_score', 0)
        if score >= 80:
            achievement = AchievementService._try_award(
                'posture_champion',
                since_date=target_date,
                metadata={'score': round(score), 'monitoring_minutes': round(monitoring_time/60)}
            )
            if achievement:
                awarded.append(achievement)

        # Consistency King: 4+ hours good posture
        good_hours = stats.get('good_duration_seconds', 0) / 3600
        if good_hours >= 4:
            achievement = AchievementService._try_award(
                'consistency_king',
                since_date=target_date,
                metadata={'good_hours': round(good_hours, 1)}
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

        # Getting Started: First day with 30+ minutes of monitoring
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
                logger.debug(f"Getting Started not earned: {monitoring_time/60:.1f} min < 30 min required")

        # Transformation: First 90%+ score
        if not AchievementRepository.has_earned_achievement('transformation'):
            score = stats.get('posture_score', 0)
            if score >= 90:
                achievement = AchievementService._try_award(
                    'transformation',
                    metadata={'score': round(score), 'date': target_date.isoformat()}
                )
                if achievement:
                    awarded.append(achievement)

        # Habit Builder and Posture Pro: Consecutive days tracking
        consecutive = AchievementService._get_consecutive_tracking_days(target_date)

        if consecutive >= 7 and not AchievementRepository.has_earned_achievement('habit_builder'):
            achievement = AchievementService._try_award(
                'habit_builder',
                metadata={'consecutive_days': consecutive}
            )
            if achievement:
                awarded.append(achievement)

        if consecutive >= 30 and not AchievementRepository.has_earned_achievement('posture_pro'):
            achievement = AchievementService._try_award(
                'posture_pro',
                metadata={'consecutive_days': consecutive}
            )
            if achievement:
                awarded.append(achievement)

        return awarded

    @staticmethod
    def _check_weekly_achievements(target_date):
        """Check weekly achievement criteria.

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
                return awarded

            # Week Warrior: 70%+ average for 7 days
            avg_score = sum(d.get('posture_score', 0) for d in history) / len(history)
            if avg_score >= 70:
                achievement = AchievementService._try_award(
                    'week_warrior',
                    since_date=target_date - timedelta(days=6),
                    metadata={'average_score': round(avg_score, 1)}
                )
                if achievement:
                    awarded.append(achievement)

            # Perfect Week: 5+ days with 80%+
            days_above_80 = sum(1 for d in history if d.get('posture_score', 0) >= 80)
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
        try:
            # Check if already earned
            if AchievementRepository.has_earned_achievement(code, since_date=since_date):
                logger.debug(f"Achievement already earned: {code}")
                return None

            # Award achievement
            achievement = AchievementRepository.award_achievement(code, metadata)
            logger.info(f"Achievement awarded: {code}")
            return achievement

        except Exception as e:
            logger.error(f"Error awarding achievement {code}: {e}")
            return None

    # Minimum events per day to count as a "tracking day" for streaks
    MIN_EVENTS_PER_TRACKING_DAY = 100  # ~100 events = ~2 minutes of monitoring minimum

    @staticmethod
    def _get_consecutive_tracking_days(end_date):
        """Count consecutive days with meaningful tracking data ending at end_date.

        A day counts as a "tracking day" only if it has at least MIN_EVENTS_PER_TRACKING_DAY
        events, ensuring the user actually monitored (not just opened the app briefly).

        Args:
            end_date: Date to count backwards from

        Returns:
            int: Number of consecutive days with meaningful tracking
        """
        from app.data.database import get_db

        db = get_db()
        consecutive = 0
        check_date = end_date

        # Check up to 60 days back (more than needed for any achievement)
        for _ in range(60):
            cursor = db.execute(
                """
                SELECT COUNT(*) as count FROM posture_event
                WHERE DATE(timestamp) = ?
                """,
                (check_date,)
            )
            row = cursor.fetchone()
            # Require minimum events to count as a tracking day
            if row['count'] >= AchievementService.MIN_EVENTS_PER_TRACKING_DAY:
                consecutive += 1
                check_date = check_date - timedelta(days=1)
            else:
                break

        return consecutive

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

            # Mark available achievements as earned or not
            available = []
            for atype in all_types:
                available.append({
                    **atype,
                    'earned': atype['code'] in earned_codes
                })

            return {
                'stats': stats,
                'earned': earned,
                'available': available,
                'recent': earned[:5]  # Most recent 5
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
