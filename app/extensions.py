from flask_socketio import SocketIO

socketio = SocketIO()


def init_db(app):
    """Initialize database with schema and WAL mode."""
    from app.data.database import init_db_schema
    init_db_schema(app)
