"""Logging configuration with systemd journal integration.

This module provides centralized logging configuration for DeskPulse with
automatic detection and graceful fallback between systemd journal and
console logging.

Usage:
    from app.core.logging import configure_logging

    def create_app(config_name='development'):
        app = Flask(__name__)
        app.config.from_object(...)
        configure_logging(app)  # Call early in factory
        ...
"""

import logging

# Graceful import for systemd journal support
# Pattern matches Story 1.4 sdnotify handling
try:
    from systemd.journal import JournalHandler

    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False
    JournalHandler = None

# Log format specification (AC4)
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(app):
    """Configure application logging with systemd journal integration.

    Sets up logging handlers based on environment:
    - When systemd.journal is available: Uses JournalHandler for systemd integration
    - When unavailable (dev/test): Falls back to StreamHandler for console output

    Log levels are read from app.config['LOG_LEVEL'] with 'INFO' as default.

    Args:
        app: Flask application instance with config loaded.

    Example:
        >>> from app.core.logging import configure_logging
        >>> configure_logging(app)
        >>> import logging
        >>> logger = logging.getLogger('deskpulse.test')
        >>> logger.info('Test message')
    """
    # Get log level from config (AC5)
    log_level_name = app.config.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create appropriate handler with graceful fallback (AC1)
    if JOURNAL_AVAILABLE:
        handler = JournalHandler()
    else:
        handler = logging.StreamHandler()

    # Apply consistent format (AC4)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)

    root_logger.addHandler(handler)

    # Set Flask app logger level
    app.logger.setLevel(log_level)

    # Quiet down noisy libraries in production
    if not app.config.get("DEBUG"):
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("engineio").setLevel(logging.WARNING)
        logging.getLogger("socketio").setLevel(logging.WARNING)

    # Log startup info
    handler_type = "JournalHandler" if JOURNAL_AVAILABLE else "StreamHandler"
    app_logger = logging.getLogger("deskpulse.app")
    app_logger.info(
        "Logging configured: handler=%s level=%s", handler_type, log_level_name
    )
