# File: app/alerts/notifier.py (NEW FILE)

"""Desktop notification system for DeskPulse posture alerts.

Manages native Linux desktop notifications via libnotify.
Browser notifications handled separately in CV pipeline (Story 3.3).
"""

import logging
import subprocess
from flask import current_app

logger = logging.getLogger('deskpulse.alert')


def send_desktop_notification(title, message):
    """
    Send native Linux desktop notification via libnotify.

    Uses notify-send (D-Bus Desktop Notifications Spec).
    Honors system Do Not Disturb settings automatically.

    Args:
        title: Notification title
        message: Notification body text

    Returns:
        bool: True if sent successfully, False otherwise
    """
    # Check config (NOTIFICATION_ENABLED from Story 1.3, validated by get_ini_bool)
    if not current_app.config.get('NOTIFICATION_ENABLED', True):
        logger.debug("Desktop notifications disabled in config")
        return False

    try:
        result = subprocess.run(
            [
                'notify-send',
                title,
                message,
                '--icon=dialog-warning',  # Visual urgency
                '--urgency=normal'         # Appropriate for posture alerts
            ],
            capture_output=True,
            text=True,
            timeout=5  # Prevent hanging
        )

        if result.returncode == 0:
            logger.info("Desktop notification sent: %s", title)
            return True
        else:
            logger.warning(
                "notify-send failed (code %s): %s", result.returncode, result.stderr
            )
            return False

    except FileNotFoundError:
        logger.error("notify-send not found - libnotify-bin not installed")
        return False
    except subprocess.TimeoutExpired:
        logger.error("notify-send timed out after 5 seconds")
        return False
    except Exception as e:
        logger.exception(f"Desktop notification failed: {e}")
        return False


def send_alert_notification(bad_posture_duration):
    """
    Send posture alert desktop notification.

    Formats duration and sends notification.
    Browser notification (SocketIO) handled in CV pipeline.

    Args:
        bad_posture_duration: Duration in seconds (expected >= 600)

    Returns:
        bool: True if sent successfully
    """
    # Defensive validation: Handle unexpected low durations
    if bad_posture_duration < 60:
        logger.warning(
            "Unexpected alert duration %ss (< 60s), using fallback message",
            bad_posture_duration
        )
        duration_text = "a while"
    else:
        # Round to nearest minute for user-friendly display
        # Example: 90 seconds → 2 minutes (rounded up)
        minutes = round(bad_posture_duration / 60)

        if minutes > 0:
            duration_text = f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            # Less than 30 seconds rounds to 0 minutes, use seconds instead
            seconds = bad_posture_duration
            duration_text = f"{seconds} second{'s' if seconds != 1 else ''}"

    # UX Design: "Gently persistent, not demanding" tone
    title = "DeskPulse"
    message = f"You've been in bad posture for {duration_text}. Time for a posture check!"

    desktop_success = send_desktop_notification(title, message)

    logger.info(
        "Alert notification: duration=%s, desktop_sent=%s",
        duration_text, desktop_success
    )

    return desktop_success


def send_confirmation(previous_bad_duration):
    """
    Send positive confirmation when posture is corrected.

    UX Design: Positive framing, celebration, brief encouragement.
    Sends desktop notification only (browser via SocketIO in pipeline).

    Args:
        previous_bad_duration: How long user was in bad posture (seconds)

    Returns:
        bool: True if notification sent successfully

    Story 3.5: Posture Correction Confirmation Feedback
    """
    # Calculate duration for logging
    minutes = previous_bad_duration // 60

    # UX Design: "Gently persistent, not demanding" - positive celebration
    title = "DeskPulse"
    message = "✓ Good posture restored! Nice work!"

    # Send desktop notification (reuses existing infrastructure)
    desktop_success = send_desktop_notification(title, message)

    logger.info(
        f"Posture correction confirmed: previous duration {minutes}m, desktop_sent={desktop_success}"
    )

    return desktop_success


def send_daily_summary(target_date=None):
    """Send end-of-day summary notification.

    Generates daily summary and delivers via:
    1. Desktop notification (libnotify - Story 3.2)
    2. SocketIO broadcast event (dashboard display)

    Args:
        target_date: Date for summary (defaults to today)

    Returns:
        dict: {
            'summary': str,              # Full summary text
            'desktop_sent': bool,        # Desktop notification success
            'socketio_sent': bool,       # SocketIO broadcast success
            'timestamp': str             # ISO 8601 timestamp
        }

    CRITICAL: Requires Flask app context (PostureAnalytics dependency).
    - Scheduler: Calls within app.app_context()
    - Manual trigger: Already has context via Flask request

    Story 4.6: End-of-Day Summary Report
    """
    from app.data.analytics import PostureAnalytics
    from app.extensions import socketio
    from datetime import datetime, date

    # Default to today if no date specified
    if target_date is None:
        target_date = date.today()

    # Generate summary with error handling (prevent crashes)
    try:
        summary = PostureAnalytics.generate_daily_summary(target_date)
    except TypeError as e:
        logger.error(f"Invalid date type for summary generation: {e}")
        return {
            'summary': 'Error generating summary',
            'desktop_sent': False,
            'socketio_sent': False,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.exception(f"Failed to generate daily summary: {e}")
        return {
            'summary': 'Error generating summary',
            'desktop_sent': False,
            'socketio_sent': False,
            'timestamp': datetime.now().isoformat()
        }

    # Send desktop notification (reuse Story 3.2 infrastructure)
    # Convert multi-line summary to single line for notification
    notification_text = summary.replace('\n', ' | ')
    desktop_success = send_desktop_notification(
        "DeskPulse Daily Summary",
        notification_text[:256]  # Truncate to 256 chars for notification limit
    )

    # Emit via SocketIO for dashboard (real-time event)
    socketio_success = False
    try:
        socketio.emit('daily_summary', {
            'summary': summary,
            'date': target_date.isoformat(),
            'timestamp': datetime.now().isoformat()
        }, broadcast=True)
        socketio_success = True
        logger.info("SocketIO daily_summary event emitted")
    except Exception as e:
        logger.exception(f"Failed to emit SocketIO daily_summary: {e}")

    logger.info(
        f"Daily summary sent for {target_date}: "
        f"desktop={desktop_success}, socketio={socketio_success}"
    )

    return {
        'summary': summary,
        'desktop_sent': desktop_success,
        'socketio_sent': socketio_success,
        'timestamp': datetime.now().isoformat()
    }
