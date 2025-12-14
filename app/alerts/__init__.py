"""
Alert and notification system.

Manages posture alert threshold tracking, desktop notifications,
browser notifications, and monitoring pause/resume controls.

Story 3.1: Alert threshold tracking and state management
Story 3.2: Desktop notifications with libnotify
Story 3.3: Browser notifications (future)
"""

from app.alerts.manager import AlertManager
from app.alerts.notifier import send_desktop_notification, send_alert_notification

__all__ = ['AlertManager', 'send_desktop_notification', 'send_alert_notification']
