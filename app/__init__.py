import atexit
from flask import Flask
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
                cv_pipeline = CVPipeline()
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
