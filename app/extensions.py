from flask_socketio import SocketIO

# CRITICAL: Use threading mode for compatibility with CV pipeline thread
# Architecture note: 2025 Flask-SocketIO recommendation for multi-threaded apps
# async_mode='threading' ensures SocketIO events don't interfere with CV thread
socketio = SocketIO(async_mode='threading')


def init_db(app):
    """Initialize database with schema and WAL mode."""
    from app.data.database import init_db_schema
    init_db_schema(app)
