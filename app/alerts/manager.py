"""
Alert threshold tracking and state management.

Manages posture alert threshold tracking, cooldown periods, and monitoring pause/resume.
Integrates with CV pipeline to track bad posture duration and trigger alerts.

Story 3.1: Alert Threshold Tracking and State Management
"""

import logging
import time

try:
    from flask import current_app
except ImportError:
    current_app = None  # For testing without Flask

logger = logging.getLogger('deskpulse.alert')


class AlertManager:
    """
    Manages posture alert threshold tracking and triggering.

    Thread Safety (CPython-specific):
    - Called from CV thread (process_posture_update @ 10 FPS)
    - Called from Flask routes (pause/resume_monitoring - Story 3.4)
    - Simple atomic operations (bool assignment, time.time(), int arithmetic)
      are thread-safe in CPython due to GIL
    - IMPORTANT: Relies on CPython GIL - not compatible with PyPy/Jython
    - State variables: monitoring_paused (bool), bad_posture_start_time (float),
      last_alert_time (float) - all atomic operations
    - No locks required: CPython GIL serializes simple assignments and reads

    Design Rationale:
    - Avoided threading.Lock to minimize performance overhead in CV thread
    - pause_monitoring() sets monitoring_paused=True → CV thread sees it next
      frame (100ms latency acceptable for user-initiated pause/resume)
    - CPython-only deployment assumption documented in architecture.md
    """

    def __init__(self):
        """Initialize alert manager with configuration from Flask app."""
        self.alert_threshold = current_app.config.get('POSTURE_ALERT_THRESHOLD', 600)  # 10 min default
        self.alert_cooldown = current_app.config.get('ALERT_COOLDOWN', 300)  # 5 min default
        self.bad_posture_start_time = None
        self.last_alert_time = None
        self.monitoring_paused = False

    def process_posture_update(self, posture_state, user_present):
        """
        Process posture state update and check for alert conditions.

        Args:
            posture_state: 'good', 'bad', or None (camera disconnected)
            user_present: bool (False when user absent or camera disconnected)

        Returns:
            dict with 3 keys:
                'should_alert': bool - True if alert should trigger now
                'duration': int - Seconds in bad posture (0 if not tracking)
                'threshold_reached': bool - True if duration >= threshold

            Note: When user absent or monitoring paused, returns:
                  {'should_alert': False, 'duration': 0, 'threshold_reached': False}
        """
        # Don't track if monitoring is paused (FR11, FR12)
        if self.monitoring_paused:
            return {
                'should_alert': False,
                'duration': 0,
                'threshold_reached': False
            }

        # Don't track if user is absent (Story 2.2 - user_present from MediaPipe)
        if not user_present or posture_state is None:
            # Reset tracking when user leaves
            if self.bad_posture_start_time is not None:
                logger.info("User absent - resetting bad posture tracking")
                self.bad_posture_start_time = None
            return {
                'should_alert': False,
                'duration': 0,
                'threshold_reached': False
            }

        current_time = time.time()

        if posture_state == 'bad':
            # Start tracking if not already
            if self.bad_posture_start_time is None:
                self.bad_posture_start_time = current_time
                logger.info("Bad posture detected - starting duration tracking")

            # Calculate duration in bad posture
            duration = int(current_time - self.bad_posture_start_time)

            # Check if threshold exceeded (FR8: default 10 minutes)
            threshold_reached = duration >= self.alert_threshold

            # Check if should alert (threshold + cooldown)
            should_alert = False
            if threshold_reached:
                if self.last_alert_time is None:
                    # First alert
                    should_alert = True
                    self.last_alert_time = current_time
                    logger.warning(
                        f"Alert threshold reached: {duration}s >= {self.alert_threshold}s"
                    )
                elif (current_time - self.last_alert_time) >= self.alert_cooldown:
                    # Cooldown expired, send reminder
                    should_alert = True
                    self.last_alert_time = current_time
                    logger.info(
                        f"Alert cooldown expired - sending reminder (duration: {duration}s)"
                    )

            return {
                'should_alert': should_alert,
                'duration': duration,
                'threshold_reached': threshold_reached
            }

        elif posture_state == 'good':
            # Reset tracking when posture improves
            if self.bad_posture_start_time is not None:
                duration = int(current_time - self.bad_posture_start_time)
                logger.info(
                    f"Good posture restored - bad duration was {duration}s"
                )
                self.bad_posture_start_time = None
                self.last_alert_time = None

            return {
                'should_alert': False,
                'duration': 0,
                'threshold_reached': False
            }

    def pause_monitoring(self):
        """Pause posture monitoring (privacy mode - FR11)."""
        self.monitoring_paused = True
        self.bad_posture_start_time = None
        self.last_alert_time = None
        logger.info("Monitoring paused by user")

    def resume_monitoring(self):
        """Resume posture monitoring (FR12)."""
        self.monitoring_paused = False
        logger.info("Monitoring resumed by user")

    def get_monitoring_status(self):
        """Get current monitoring status (FR13)."""
        return {
            'monitoring_active': not self.monitoring_paused,
            'threshold_seconds': self.alert_threshold,
            'cooldown_seconds': self.alert_cooldown
        }
