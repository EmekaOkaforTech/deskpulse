"""
Alert and notification system.

Manages posture alert threshold tracking, desktop notifications,
browser notifications, and monitoring pause/resume controls.

Story 3.1: Alert threshold tracking and state management
Story 3.2: Desktop notifications (future)
Story 3.3: Browser notifications (future)
"""

from app.alerts.manager import AlertManager

__all__ = ['AlertManager']
