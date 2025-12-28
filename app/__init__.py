import atexit
from flask import Flask, current_app
from flask_talisman import Talisman
from app.extensions import socketio, init_db
from app.core import configure_logging

# Global CV pipeline instance (singleton pattern)
cv_pipeline = None


def create_app(config_name="development"):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(f"app.config.{config_name.capitalize()}Config")

    # Configure logging
    configure_logging(app)

    # Enterprise Security: Content Security Policy (CSP) headers
    # Protects against XSS, clickjacking, code injection attacks
    # Reference: https://binaryscripts.com/flask/2025/02/10/securing-flask-applications-with-content-security-policies-csp.html
    if not app.config.get('TESTING', False):
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
    with app.app_context():
        from app.main import events  # noqa: F401

    # Start CV pipeline in dedicated thread (Story 2.4)
    # Skip in test environment to avoid thread interference
    # Must run within app context to access config
    if not app.config.get('TESTING', False):
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
            else:
                app.logger.info("CV pipeline already running")
    else:
        app.logger.info("CV pipeline disabled in test mode")

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
