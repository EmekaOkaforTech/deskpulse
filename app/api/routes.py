"""API routes for DeskPulse analytics and statistics.

Enterprise-Grade REST API:
- Explicit HTTP methods for security
- Comprehensive error handling with logging
- Proper JSON serialization (ISO 8601 dates)
- Type-safe responses
"""

from flask import jsonify
from datetime import date
from app.api import bp
from app.data.analytics import PostureAnalytics
import logging

logger = logging.getLogger('deskpulse.api')


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
        stats = PostureAnalytics.calculate_daily_stats(date.today())

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
        history = PostureAnalytics.get_7_day_history()

        # Convert date objects to ISO 8601 strings for JSON serialization
        # Required for all date objects in the history array
        for day_stats in history:
            day_stats['date'] = day_stats['date'].isoformat()  # "2025-12-19"

        logger.debug(f"Retrieved 7-day history: {len(history)} days")
        return jsonify({'history': history}), 200

    except Exception:
        logger.exception("Failed to get history")  # Exception auto-included by logger.exception()
        return jsonify({'error': 'Failed to retrieve history'}), 500
