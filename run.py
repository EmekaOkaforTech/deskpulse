"""DeskPulse Application Entry Point.

Enterprise-grade startup with clean console output.
Suppresses non-critical TensorFlow/MediaPipe warnings on ARM processors.
"""
import os
import sys
import warnings
import contextlib

# Suppress TensorFlow/MediaPipe warnings BEFORE any imports
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TF logs (ERROR only)
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Suppress oneDNN messages
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'  # Disable GPU (not available on Pi)
os.environ['GLOG_minloglevel'] = '2'  # Suppress glog (used by MediaPipe)

# Suppress Python warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)


@contextlib.contextmanager
def suppress_stderr():
    """Suppress C++ stderr output by redirecting file descriptor."""
    # Save original stderr file descriptor
    stderr_fd = sys.stderr.fileno()
    saved_stderr_fd = os.dup(stderr_fd)

    # Open /dev/null and redirect stderr to it
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, stderr_fd)
    os.close(devnull)

    try:
        yield
    finally:
        # Restore original stderr
        os.dup2(saved_stderr_fd, stderr_fd)
        os.close(saved_stderr_fd)


# Import with stderr suppressed to catch C++ warnings during model loading
with suppress_stderr():
    from app import create_app
    from app.extensions import socketio

app = create_app("development")

if __name__ == "__main__":
    # SECURITY: Use HOST from config (defaults to 127.0.0.1 per NFR-S2)
    # NOTE: use_reloader=False to prevent duplicate processes competing for camera
    socketio.run(
        app,
        host=app.config.get("HOST", "127.0.0.1"),
        port=app.config.get("PORT", 5000),
        debug=True,
        use_reloader=False,  # Disable reloader (camera access issue)
        allow_unsafe_werkzeug=True,  # Required for development mode
    )
