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
