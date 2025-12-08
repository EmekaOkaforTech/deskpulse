"""Core application utilities.

This package provides core utilities for DeskPulse:
- Logging configuration with systemd journal integration
- Application constants
- Custom exception classes
"""

from app.core.logging import configure_logging

__all__ = ["configure_logging"]
