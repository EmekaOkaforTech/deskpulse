"""API routes for DeskPulse analytics and statistics.

Enterprise-Grade REST API:
- Explicit HTTP methods for security
- Comprehensive error handling with logging
- Proper JSON serialization (ISO 8601 dates)
- Type-safe responses
"""

from flask import jsonify, current_app
from datetime import date
from app.api import bp
from app.data.analytics import PostureAnalytics
import logging

logger = logging.getLogger('deskpulse.api')


def _get_pause_timestamp():
    """
    Get pause_timestamp from CV pipeline (works in both Pi and Standalone modes).

    Returns:
        datetime or None: The pause timestamp if monitoring is paused, else None

    Location of CV pipeline:
        - Pi/Server mode: current_app.cv_pipeline (stored on Flask app)
        - Standalone mode: backend_thread via Flask app config

    CRITICAL: This function must return a valid pause_timestamp when monitoring
    is paused, otherwise stats will keep increasing (using datetime.now()).
    """
    logger.info("=== _get_pause_timestamp() called ===")
    pause_timestamp = None

    # Try Pi/Server mode first via current_app.cv_pipeline (most reliable)
    try:
        if hasattr(current_app, 'cv_pipeline') and current_app.cv_pipeline:
            if hasattr(current_app.cv_pipeline, 'alert_manager') and current_app.cv_pipeline.alert_manager:
                am = current_app.cv_pipeline.alert_manager
                logger.debug(f"Pi mode (current_app): monitoring_paused={am.monitoring_paused}, pause_timestamp={am.pause_timestamp}")
                if am.monitoring_paused:
                    pause_timestamp = am.pause_timestamp
                    logger.info(f"Got pause_timestamp from current_app.cv_pipeline: {pause_timestamp}")
                    return pause_timestamp
                else:
                    logger.debug("Pi mode: monitoring is active (not paused)")
                    return None
    except Exception as e:
        logger.warning(f"Pi mode current_app.cv_pipeline check failed: {e}")

    # Fallback: Try module-level global (legacy support)
    try:
        import app as app_module
        if hasattr(app_module, 'cv_pipeline') and app_module.cv_pipeline:
            if hasattr(app_module.cv_pipeline, 'alert_manager') and app_module.cv_pipeline.alert_manager:
                am = app_module.cv_pipeline.alert_manager
                logger.debug(f"Pi mode (module): monitoring_paused={am.monitoring_paused}, pause_timestamp={am.pause_timestamp}")
                if am.monitoring_paused:
                    pause_timestamp = am.pause_timestamp
                    logger.info(f"Got pause_timestamp from app module: {pause_timestamp}")
                    return pause_timestamp
                else:
                    logger.debug("Pi mode (module): monitoring is active (not paused)")
                    return None
    except Exception as e:
        logger.warning(f"Pi mode module cv_pipeline check failed: {e}")

    # Try Standalone mode (via Flask app config - avoids PyInstaller module issues)
    try:
        backend = current_app.config.get('BACKEND_THREAD')

        # Diagnostic logging for standalone mode
        if backend is None:
            logger.debug("Standalone mode: BACKEND_THREAD not in config (Pi mode)")
            return None

        if backend.cv_pipeline is None:
            logger.warning("Standalone mode: backend.cv_pipeline is None")
            return None

        if not hasattr(backend.cv_pipeline, 'alert_manager') or backend.cv_pipeline.alert_manager is None:
            logger.warning("Standalone mode: alert_manager is None or missing")
            return None

        am = backend.cv_pipeline.alert_manager
        logger.debug(f"Standalone mode: monitoring_paused={am.monitoring_paused}, pause_timestamp={am.pause_timestamp}")

        if am.monitoring_paused:
            pause_timestamp = am.pause_timestamp
            if pause_timestamp is None:
                logger.error("BUG: monitoring_paused=True but pause_timestamp is None!")
            else:
                logger.info(f"Got pause_timestamp from backend_thread: {pause_timestamp}")
            return pause_timestamp
        else:
            # Monitoring is active (not paused) - this is normal
            logger.debug("Standalone mode: monitoring is active (not paused)")
            return None

    except Exception as e:
        # CRITICAL: Log at WARNING level so we can diagnose issues
        logger.warning(f"Standalone mode backend check failed: {e}", exc_info=True)

    logger.info(f"=== _get_pause_timestamp() returning: {pause_timestamp} ===")
    return pause_timestamp


def _get_monitoring_status():
    """
    Get monitoring status from CV pipeline (works in both Pi and Standalone modes).

    Returns:
        dict: {'monitoring_active': bool, 'threshold_seconds': int, 'cooldown_seconds': int}
    """
    default_status = {
        'monitoring_active': True,
        'threshold_seconds': 600,
        'cooldown_seconds': 300
    }

    # CRITICAL FIX: Try current_app.cv_pipeline FIRST (matches _get_pause_timestamp)
    try:
        if hasattr(current_app, 'cv_pipeline') and current_app.cv_pipeline:
            if hasattr(current_app.cv_pipeline, 'alert_manager') and current_app.cv_pipeline.alert_manager:
                status = current_app.cv_pipeline.alert_manager.get_monitoring_status()
                logger.debug(f"Pi mode status (current_app): {status}")
                return status
    except Exception as e:
        logger.warning(f"current_app.cv_pipeline status check failed: {e}")

    # Fallback: Try module-level global (legacy support)
    try:
        import app as app_module
        if hasattr(app_module, 'cv_pipeline') and app_module.cv_pipeline:
            if hasattr(app_module.cv_pipeline, 'alert_manager') and app_module.cv_pipeline.alert_manager:
                status = app_module.cv_pipeline.alert_manager.get_monitoring_status()
                logger.debug(f"Pi mode status (module): {status}")
                return status
    except Exception as e:
        logger.warning(f"app_module.cv_pipeline status check failed: {e}")

    # Try Standalone mode (via Flask app config - avoids PyInstaller module issues)
    try:
        backend = current_app.config.get('BACKEND_THREAD')

        if backend is None:
            logger.debug("_get_monitoring_status: BACKEND_THREAD not in config (Pi mode)")
            return default_status

        if backend.cv_pipeline is None:
            logger.warning("_get_monitoring_status: backend.cv_pipeline is None")
            return default_status

        if not hasattr(backend.cv_pipeline, 'alert_manager') or backend.cv_pipeline.alert_manager is None:
            logger.warning("_get_monitoring_status: alert_manager is None or missing")
            return default_status

        status = backend.cv_pipeline.alert_manager.get_monitoring_status()
        logger.debug(f"Standalone mode status: {status}")
        return status

    except Exception as e:
        logger.warning(f"Standalone mode status check failed: {e}", exc_info=True)

    return default_status


@bp.route('/monitoring-status', methods=['GET'])
def get_monitoring_status():
    """Get current monitoring status (active or paused).

    Returns:
        JSON: Monitoring status dict with 200 status
        {
            "monitoring_active": true,       # false when paused
            "threshold_seconds": 600,        # bad posture alert threshold
            "cooldown_seconds": 300          # alert cooldown period
        }
    """
    try:
        status = _get_monitoring_status()
        logger.info(f"GET /monitoring-status: active={status['monitoring_active']}")
        return jsonify(status), 200
    except Exception:
        logger.exception("Failed to get monitoring status")
        return jsonify({'error': 'Failed to get monitoring status'}), 500


@bp.route('/monitoring/pause', methods=['POST'])
def pause_monitoring():
    """Pause posture monitoring (REST API for standalone mode).

    Returns:
        JSON: Updated monitoring status with 200 status
        {"success": true, "monitoring_active": false}
    """
    logger.info("=== PAUSE MONITORING API CALLED ===")
    try:
        # CRITICAL FIX: Try current_app.cv_pipeline FIRST (matches _get_pause_timestamp)
        # This ensures pause state is set on the SAME object that _get_pause_timestamp checks
        try:
            if hasattr(current_app, 'cv_pipeline') and current_app.cv_pipeline:
                if hasattr(current_app.cv_pipeline, 'alert_manager') and current_app.cv_pipeline.alert_manager:
                    # Record pause marker BEFORE pausing
                    current_state = current_app.cv_pipeline.last_posture_state
                    marker_state = current_state if current_state in ('good', 'bad') else 'good'
                    try:
                        from app.data.repository import PostureEventRepository
                        PostureEventRepository.insert_posture_event(
                            posture_state=marker_state,
                            user_present=True,
                            confidence_score=0.95 if current_state in ('good', 'bad') else 0.5,
                            metadata={'monitoring_paused': True}
                        )
                        logger.info(f"Pause marker event recorded: {marker_state} (original: {current_state})")
                    except Exception as e:
                        logger.warning(f"Failed to record pause marker: {e}")
                    current_app.cv_pipeline.alert_manager.pause_monitoring()
                    logger.info(f"Monitoring paused via current_app.cv_pipeline, pause_timestamp={current_app.cv_pipeline.alert_manager.pause_timestamp}")
                    return jsonify({'success': True, 'monitoring_active': False}), 200
        except Exception as e:
            logger.debug(f"current_app.cv_pipeline pause failed: {e}")

        # Fallback: Try module-level global (legacy support)
        try:
            import app as app_module
            if hasattr(app_module, 'cv_pipeline') and app_module.cv_pipeline:
                if app_module.cv_pipeline.alert_manager:
                    current_state = app_module.cv_pipeline.last_posture_state
                    marker_state = current_state if current_state in ('good', 'bad') else 'good'
                    try:
                        from app.data.repository import PostureEventRepository
                        PostureEventRepository.insert_posture_event(
                            posture_state=marker_state,
                            user_present=True,
                            confidence_score=0.95 if current_state in ('good', 'bad') else 0.5,
                            metadata={'monitoring_paused': True}
                        )
                        logger.info(f"Pause marker event recorded (module): {marker_state}")
                    except Exception as e:
                        logger.warning(f"Failed to record pause marker: {e}")
                    app_module.cv_pipeline.alert_manager.pause_monitoring()
                    logger.info(f"Monitoring paused via app_module.cv_pipeline, pause_timestamp={app_module.cv_pipeline.alert_manager.pause_timestamp}")
                    return jsonify({'success': True, 'monitoring_active': False}), 200
        except Exception as e:
            logger.debug(f"app_module.cv_pipeline pause failed: {e}")

        # Try Standalone mode (via Flask app config - avoids PyInstaller module issues)
        try:
            backend = current_app.config.get('BACKEND_THREAD')
            logger.info(f"Standalone mode: BACKEND_THREAD = {backend}")
            if backend:
                logger.info(f"Backend cv_pipeline: {backend.cv_pipeline}")
                logger.info(f"Backend cv_pipeline.alert_manager: {backend.cv_pipeline.alert_manager if backend.cv_pipeline else None}")
                # Use backend.pause_monitoring() to ensure SharedState is updated
                backend.pause_monitoring()
                # Verify pause was applied
                if backend.cv_pipeline and backend.cv_pipeline.alert_manager:
                    am = backend.cv_pipeline.alert_manager
                    logger.info(f"After pause: monitoring_paused={am.monitoring_paused}, pause_timestamp={am.pause_timestamp}")
                logger.info("Monitoring paused via REST API (standalone mode)")
                return jsonify({'success': True, 'monitoring_active': False}), 200
            else:
                logger.warning("pause_monitoring: BACKEND_THREAD not in config")
        except Exception as e:
            logger.warning(f"Standalone mode pause failed: {e}", exc_info=True)

        logger.error("=== PAUSE FAILED: No CV pipeline available ===")
        return jsonify({'success': False, 'error': 'CV pipeline not available'}), 500

    except Exception:
        logger.exception("Failed to pause monitoring")
        return jsonify({'success': False, 'error': 'Failed to pause monitoring'}), 500


@bp.route('/monitoring/resume', methods=['POST'])
def resume_monitoring():
    """Resume posture monitoring (REST API for standalone mode).

    Returns:
        JSON: Updated monitoring status with 200 status
        {"success": true, "monitoring_active": true}
    """
    logger.info("=== RESUME MONITORING API CALLED ===")
    try:
        # CRITICAL FIX: Try current_app.cv_pipeline FIRST (matches _get_pause_timestamp)
        # This ensures resume state is set on the SAME object that _get_pause_timestamp checks
        try:
            if hasattr(current_app, 'cv_pipeline') and current_app.cv_pipeline:
                if hasattr(current_app.cv_pipeline, 'alert_manager') and current_app.cv_pipeline.alert_manager:
                    current_app.cv_pipeline.alert_manager.resume_monitoring()
                    # Record resume marker AFTER resuming
                    current_state = current_app.cv_pipeline.last_posture_state
                    marker_state = current_state if current_state in ('good', 'bad') else 'good'
                    try:
                        from app.data.repository import PostureEventRepository
                        PostureEventRepository.insert_posture_event(
                            posture_state=marker_state,
                            user_present=True,
                            confidence_score=0.95 if current_state in ('good', 'bad') else 0.5,
                            metadata={'resume_marker': True}
                        )
                        logger.info(f"Resume marker event recorded: {marker_state} (original: {current_state})")
                    except Exception as e:
                        logger.warning(f"Failed to record resume marker: {e}")
                    logger.info(f"Monitoring resumed via current_app.cv_pipeline, monitoring_paused={current_app.cv_pipeline.alert_manager.monitoring_paused}")
                    return jsonify({'success': True, 'monitoring_active': True}), 200
        except Exception as e:
            logger.debug(f"current_app.cv_pipeline resume failed: {e}")

        # Fallback: Try module-level global (legacy support)
        try:
            import app as app_module
            if hasattr(app_module, 'cv_pipeline') and app_module.cv_pipeline:
                if app_module.cv_pipeline.alert_manager:
                    app_module.cv_pipeline.alert_manager.resume_monitoring()
                    current_state = app_module.cv_pipeline.last_posture_state
                    marker_state = current_state if current_state in ('good', 'bad') else 'good'
                    try:
                        from app.data.repository import PostureEventRepository
                        PostureEventRepository.insert_posture_event(
                            posture_state=marker_state,
                            user_present=True,
                            confidence_score=0.95 if current_state in ('good', 'bad') else 0.5,
                            metadata={'resume_marker': True}
                        )
                        logger.info(f"Resume marker event recorded (module): {marker_state}")
                    except Exception as e:
                        logger.warning(f"Failed to record resume marker: {e}")
                    logger.info(f"Monitoring resumed via app_module.cv_pipeline")
                    return jsonify({'success': True, 'monitoring_active': True}), 200
        except Exception as e:
            logger.debug(f"app_module.cv_pipeline resume failed: {e}")

        # Try Standalone mode (via Flask app config - avoids PyInstaller module issues)
        try:
            backend = current_app.config.get('BACKEND_THREAD')
            logger.info(f"Standalone mode: BACKEND_THREAD = {backend}")
            if backend:
                # Use backend.resume_monitoring() to ensure SharedState is updated
                backend.resume_monitoring()
                # Verify resume was applied
                if backend.cv_pipeline and backend.cv_pipeline.alert_manager:
                    am = backend.cv_pipeline.alert_manager
                    logger.info(f"After resume: monitoring_paused={am.monitoring_paused}, pause_timestamp={am.pause_timestamp}")
                logger.info("Monitoring resumed via REST API (standalone mode)")
                return jsonify({'success': True, 'monitoring_active': True}), 200
            else:
                logger.warning("resume_monitoring: BACKEND_THREAD not in config")
        except Exception as e:
            logger.warning(f"Standalone mode resume failed: {e}", exc_info=True)

        logger.error("=== RESUME FAILED: No CV pipeline available ===")
        return jsonify({'success': False, 'error': 'CV pipeline not available'}), 500

    except Exception:
        logger.exception("Failed to resume monitoring")
        return jsonify({'success': False, 'error': 'Failed to resume monitoring'}), 500


@bp.route('/stats/today', methods=['GET'])
def get_today_stats():
    """Get posture statistics for today.

    Returns:
        JSON: Daily stats dict with 200 status
        {
            "date": "2025-12-19",                    # ISO 8601 date string
            "good_duration_seconds": 7200,
            "bad_duration_seconds": 1800,
            "user_present_duration_seconds": 9000,
            "posture_score": 80.0,                   # 0-100 percentage
            "total_events": 42
        }

    Error Response:
        JSON: {"error": "Failed to retrieve statistics"} with 500 status
    """
    try:
        # Get pause_timestamp if monitoring is paused (CRITICAL for accurate stats)
        pause_timestamp = _get_pause_timestamp()
        logger.info(f"get_today_stats: pause_timestamp={pause_timestamp}")

        stats = PostureAnalytics.calculate_daily_stats(date.today(), pause_timestamp=pause_timestamp)

        # Convert date object to ISO 8601 string for JSON serialization
        # Why needed: Python date objects are not JSON-serializable by default
        # Without this: TypeError: Object of type date is not JSON serializable
        # Pattern: Matches database.py ISO 8601 adapter pattern (database.py:51-63)
        stats['date'] = stats['date'].isoformat()  # "2025-12-19"

        logger.debug(f"Today's stats: score={stats['posture_score']}%, events={stats['total_events']}")
        return jsonify(stats), 200

    except Exception:
        logger.exception("Failed to get today's stats")  # Exception auto-included by logger.exception()
        return jsonify({'error': 'Failed to retrieve statistics'}), 500


@bp.route('/stats/history', methods=['GET'])
def get_history():
    """Get 7-day posture history (6 days ago through today).

    Returns:
        JSON: {"history": [stats_dict, ...]} with 200 status
        {
            "history": [
                {
                    "date": "2025-12-13",
                    "good_duration_seconds": 5400,
                    "bad_duration_seconds": 2700,
                    "user_present_duration_seconds": 8100,
                    "posture_score": 66.7,
                    "total_events": 28
                },
                ... (7 total entries, oldest to newest)
            ]
        }

    Error Response:
        JSON: {"error": "Failed to retrieve history"} with 500 status
    """
    try:
        # Get pause_timestamp if monitoring is paused (CRITICAL for accurate today's stats)
        pause_timestamp = _get_pause_timestamp()

        history = PostureAnalytics.get_7_day_history(pause_timestamp=pause_timestamp)

        # Convert date objects to ISO 8601 strings for JSON serialization
        # Required for all date objects in the history array
        for day_stats in history:
            day_stats['date'] = day_stats['date'].isoformat()  # "2025-12-19"

        logger.debug(f"Retrieved 7-day history: {len(history)} days")
        return jsonify({'history': history}), 200

    except Exception:
        logger.exception("Failed to get history")  # Exception auto-included by logger.exception()
        return jsonify({'error': 'Failed to retrieve history'}), 500


@bp.route('/stats/trend', methods=['GET'])
def get_trend():
    """Get posture improvement trend analysis.

    Returns:
        JSON: Trend analysis dict with 200 status
        {
            "trend": "improving",                       # 'improving', 'stable', 'declining', 'insufficient_data'
            "average_score": 68.5,                      # 0-100 percentage (1 decimal)
            "score_change": 12.3,                       # Points change first → last day (1 decimal)
            "best_day": {                               # Daily stats dict for best day
                "date": "2025-12-27",
                "posture_score": 75.2,
                ...
            },
            "improvement_message": "You've improved 12.3 points this week! Keep it up!"
        }

    Error Response:
        JSON: {"error": "Failed to calculate trend"} with 500 status
    """
    try:
        # Get pause_timestamp if monitoring is paused (CRITICAL for accurate today's stats)
        pause_timestamp = _get_pause_timestamp()

        # Get 7-day history (reuses existing method from Story 4.2)
        history = PostureAnalytics.get_7_day_history(pause_timestamp=pause_timestamp)

        # Calculate trend analysis
        trend_data = PostureAnalytics.calculate_trend(history)

        # Convert date objects to ISO 8601 strings for JSON serialization
        # best_day may contain date object that needs serialization
        if trend_data['best_day'] and 'date' in trend_data['best_day']:
            trend_data['best_day']['date'] = trend_data['best_day']['date'].isoformat()

        logger.debug(f"Trend data: {trend_data['trend']}, change={trend_data['score_change']}")
        return jsonify(trend_data), 200

    except Exception:
        logger.exception("Failed to get trend")  # Exception auto-included by logger.exception()
        return jsonify({'error': 'Failed to calculate trend'}), 500


# ============================================
# Achievement API Endpoints - Phase 2
# ============================================

@bp.route('/achievements', methods=['GET'])
def get_achievements():
    """Get achievement summary including earned, available, and stats.

    Returns:
        JSON: Achievement summary with 200 status
        {
            "stats": {
                "total_earned": 5,
                "total_available": 13,
                "total_points": 85,
                "completion_percentage": 38.5,
                "by_category": {"daily": 3, "milestone": 2}
            },
            "earned": [...],
            "available": [...],
            "recent": [...]
        }

    Error Response:
        JSON: {"error": "Failed to retrieve achievements"} with 500 status
    """
    try:
        from app.data.achievements import AchievementService
        summary = AchievementService.get_achievement_summary()
        logger.debug(f"Achievement summary: {summary['stats']['total_earned']}/{summary['stats']['total_available']} earned")
        return jsonify(summary), 200

    except Exception:
        logger.exception("Failed to get achievements")
        return jsonify({'error': 'Failed to retrieve achievements'}), 500


@bp.route('/achievements/check', methods=['POST'])
def check_achievements():
    """Check and award any newly earned achievements.

    Called after stats update to check if user has earned new achievements.
    This is idempotent - calling multiple times won't duplicate awards.

    Returns:
        JSON: List of newly awarded achievements with 200 status
        {
            "newly_awarded": [
                {
                    "code": "posture_champion",
                    "name": "Posture Champion",
                    "icon": "🏆",
                    "points": 15,
                    ...
                }
            ],
            "count": 1
        }

    Error Response:
        JSON: {"error": "Failed to check achievements"} with 500 status
    """
    try:
        from app.data.achievements import AchievementService

        # Get today's stats for achievement checking
        pause_timestamp = _get_pause_timestamp()
        stats = PostureAnalytics.calculate_daily_stats(date.today(), pause_timestamp=pause_timestamp)

        # Check and award achievements
        newly_awarded = AchievementService.check_and_award_achievements(stats)

        logger.info(f"Achievement check complete: {len(newly_awarded)} newly awarded")
        return jsonify({
            'newly_awarded': newly_awarded,
            'count': len(newly_awarded)
        }), 200

    except Exception:
        logger.exception("Failed to check achievements")
        return jsonify({'error': 'Failed to check achievements'}), 500


@bp.route('/achievements/unnotified', methods=['GET'])
def get_unnotified_achievements():
    """Get achievements that haven't been shown to the user yet.

    Used by frontend to display achievement notifications.

    Returns:
        JSON: List of unnotified achievements with 200 status
        {
            "achievements": [...],
            "count": 2
        }
    """
    try:
        from app.data.achievements import AchievementService
        achievements = AchievementService.get_unnotified_achievements()

        return jsonify({
            'achievements': achievements,
            'count': len(achievements)
        }), 200

    except Exception:
        logger.exception("Failed to get unnotified achievements")
        return jsonify({'error': 'Failed to retrieve achievements'}), 500


@bp.route('/achievements/<int:earned_id>/notified', methods=['POST'])
def mark_achievement_notified(earned_id):
    """Mark an achievement as notified (user has seen it).

    Args:
        earned_id: The earned achievement ID from URL

    Returns:
        JSON: {"success": true} with 200 status

    Error Response:
        JSON: {"error": "..."} with 500 status
    """
    try:
        from app.data.achievements import AchievementService
        AchievementService.mark_notified(earned_id)

        logger.debug(f"Achievement {earned_id} marked as notified")
        return jsonify({'success': True}), 200

    except Exception:
        logger.exception(f"Failed to mark achievement {earned_id} as notified")
        return jsonify({'error': 'Failed to update achievement'}), 500
