import atexit
from flask import Flask, current_app
from flask_talisman import Talisman
from app.extensions import init_db
from app.core import configure_logging

# Conditional SocketIO import for dual-mode support (Story 8.4)
# Only import if Flask-SocketIO is available (Pi mode)
# Windows standalone mode doesn't need SocketIO
try:
    from app.extensions import socketio
except ImportError:
    socketio = None  # Standalone mode without Flask-SocketIO

# Global CV pipeline instance (singleton pattern)
cv_pipeline = None


def create_app(config_name="development", database_path=None, standalone_mode=False):
    """
    Create Flask application.

    Args:
        config_name: Configuration name (development, production, testing, standalone)
        database_path: Optional custom database path (for standalone mode)
        standalone_mode: If True, skip SocketIO, Talisman, scheduler (for standalone Windows)

    Returns:
        Flask app instance
    """
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(f"app.config.{config_name.capitalize()}Config")

    # Override database path if provided (for standalone mode)
    if database_path:
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_path}'
        app.logger.info(f"Using custom database: {database_path}")

    # Configure logging
    configure_logging(app)

    # Store standalone_mode in config for template access
    app.config['STANDALONE_MODE'] = standalone_mode

    # Enterprise Security: Content Security Policy (CSP) headers
    # Protects against XSS, clickjacking, code injection attacks
    # Reference: https://binaryscripts.com/flask/2025/02/10/securing-flask-applications-with-content-security-policies-csp.html
    # Skip in standalone mode (no web access needed)
    if not app.config.get('TESTING', False) and not standalone_mode:
        # CSP Configuration for production/development
        csp = {
            'default-src': ["'self'"],  # Default: only same-origin
            'script-src': [
                "'self'",
                'https://cdn.socket.io',  # SocketIO client library
                "'unsafe-inline'"  # Required for inline event handlers (minimize in production)
            ],
            'style-src': [
                "'self'",
                'https://cdn.jsdelivr.net',  # Pico CSS framework
                "'unsafe-inline'"  # Required for <style> tags in base.html
            ],
            'connect-src': [
                "'self'",
                'ws://*:5000',  # WebSocket all IPs on port 5000 (local network)
                'ws://localhost:5000',  # WebSocket local development
                'ws://127.0.0.1:5000',  # WebSocket localhost
                'wss://deskpulse.local',  # WebSocket production (HTTPS)
                'wss://*.local',  # WebSocket wildcard for local network
                # Reference: https://github.com/socketio/socket.io/discussions/4269
                # Safari requires explicit wss:// in connect-src for WebSockets
            ],
            'img-src': [
                "'self'",
                'data:',  # Base64-encoded camera feed images
            ],
            'font-src': ["'self'"],
            'object-src': ["'none'"],  # Block plugins (Flash, Java)
            'frame-ancestors': ["'none'"],  # Prevent clickjacking (X-Frame-Options)
            'base-uri': ["'self'"],  # Restrict <base> tag
            'form-action': ["'self'"],  # Only allow forms to submit to same origin
        }

        # Initialize Talisman with CSP and security headers
        # force_https=False for local development (Pi doesn't use HTTPS by default)
        # Reference: https://github.com/GoogleCloudPlatform/flask-talisman
        Talisman(
            app,
            content_security_policy=csp,
            content_security_policy_nonce_in=['script-src'],  # Nonce support for inline scripts
            force_https=False,  # Allow HTTP for local Raspberry Pi deployment
            strict_transport_security=False,  # Disable HSTS for HTTP
            session_cookie_secure=False,  # Allow cookies over HTTP (local network)
            referrer_policy='strict-origin-when-cross-origin',
            feature_policy={
                'geolocation': "'none'",
                'camera': "'none'",  # Block browser camera (we use server-side)
                'microphone': "'none'"
            }
        )

    # Initialize extensions
    init_db(app)

    # Initialize SocketIO AFTER app created, BEFORE blueprint registration
    # Architecture: async_mode='threading' for CV pipeline compatibility
    # Skip in standalone mode (uses local IPC instead)
    if not standalone_mode and socketio is not None:
        socketio.init_app(
            app,
            cors_allowed_origins="*",  # Allow cross-origin for local network access
            logger=True,
            engineio_logger=False,  # Reduce log spam
            ping_timeout=10,  # 10 seconds to respond to ping
            ping_interval=25  # Send ping every 25 seconds
        )

    # Register blueprints
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # Import SocketIO event handlers (registers @socketio.on decorators)
    # CRITICAL: Import AFTER socketio.init_app() to ensure app context
    # Skip in standalone mode (no SocketIO)
    if not standalone_mode and socketio is not None:
        with app.app_context():
            from app.main import events  # noqa: F401

    # Start CV pipeline in dedicated thread (Story 2.4)
    # Skip in test environment to avoid thread interference
    # Skip in standalone mode (managed externally by backend_thread.py)
    # Must run within app context to access config
    if not app.config.get('TESTING', False) and not standalone_mode:
        with app.app_context():
            global cv_pipeline
            from app.cv.pipeline import CVPipeline

            # Only create pipeline if none exists or previous one stopped
            if cv_pipeline is None or not cv_pipeline.running:
                # Pass actual Flask app object (not proxy) for background thread context
                # Story 3.6: Fix alert notifications - CV thread needs app context
                cv_pipeline = CVPipeline(app=current_app._get_current_object())
                if not cv_pipeline.start():
                    app.logger.error(
                        "Failed to start CV pipeline - dashboard will show no "
                        "video feed"
                    )
                else:
                    app.logger.info("CV pipeline started successfully")
                    # Register cleanup on process exit
                    atexit.register(cleanup_cv_pipeline)
                # Store on Flask app for reliable access via current_app
                app.cv_pipeline = cv_pipeline
            else:
                app.logger.info("CV pipeline already running")
    elif standalone_mode:
        app.logger.info("CV pipeline will be managed by standalone mode")
    else:
        app.logger.info("CV pipeline disabled in test mode")

    # Start daily scheduler (Story 4.6)
    # Skip in test environment to avoid thread interference
    # Skip in standalone mode (not needed for Windows)
    if not app.config.get('TESTING', False) and not standalone_mode:
        with app.app_context():
            from app.system.scheduler import start_scheduler

            # Start scheduler (returns instance for potential manual control)
            scheduler = start_scheduler(app)

            if scheduler and scheduler.running:
                app.logger.info("Daily scheduler started successfully")
            else:
                app.logger.error(
                    "Failed to start daily scheduler - end-of-day summaries "
                    "will not be sent automatically"
                )
    elif standalone_mode:
        app.logger.info("Daily scheduler disabled in standalone mode")
    else:
        app.logger.info("Daily scheduler disabled in test mode")

    return app


def cleanup_cv_pipeline():
    """
    Cleanup function for CV pipeline (called on application shutdown).

    Note: With daemon threads, this is optional. Include for explicit cleanup
    if needed for testing or graceful shutdown scenarios.
    """
    global cv_pipeline
    if cv_pipeline:
        cv_pipeline.stop()
