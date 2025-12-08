"""WSGI entry point for DeskPulse.

This module serves as the production entry point for DeskPulse when running
under systemd. It handles:
- systemd readiness notification (READY=1)
- Watchdog ping integration
- Security-first network binding (localhost by default)
"""

import atexit
import os

from app import create_app
from app.extensions import socketio
from app.system.watchdog import watchdog

# Create Flask application
app = create_app("systemd")

# Signal readiness to systemd after Flask app is created
watchdog.notify_ready()
watchdog.notify_status("DeskPulse started successfully")

# Start watchdog ping thread
watchdog.start()


# Register cleanup on application shutdown
def cleanup():
    """Clean up resources on application shutdown."""
    watchdog.notify_stopping()
    watchdog.stop()


atexit.register(cleanup)


if __name__ == "__main__":
    # SECURITY: Default to localhost binding (127.0.0.1) for security
    # For local network access, set FLASK_HOST=0.0.0.0 via environment
    # or systemd override file at /etc/systemd/system/deskpulse.service.d/override.conf
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5000"))

    socketio.run(app, host=host, port=port)
