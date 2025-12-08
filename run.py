from app import create_app
from app.extensions import socketio

app = create_app("development")

if __name__ == "__main__":
    # SECURITY: Use HOST from config (defaults to 127.0.0.1 per NFR-S2)
    socketio.run(
        app,
        host=app.config.get("HOST", "127.0.0.1"),
        port=app.config.get("PORT", 5000),
        debug=True,
    )
