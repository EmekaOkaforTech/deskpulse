from flask import Flask
from app.extensions import socketio, init_db
from app.core import configure_logging


def create_app(config_name="development"):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(f"app.config.{config_name.capitalize()}Config")

    # Configure logging
    configure_logging(app)

    # Initialize extensions
    init_db(app)
    # SECURITY: Use specific CORS origins list (do NOT use "*" in production)
    # Origins are configurable via config.ini [dashboard] cors_origins
    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get("CORS_ALLOWED_ORIGINS", []),
    )

    # Register blueprints
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    return app
