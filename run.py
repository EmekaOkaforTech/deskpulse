"""DeskPulse Application Entry Point.

Enterprise-grade startup with clean console output.
Suppresses non-critical TensorFlow/MediaPipe warnings on ARM processors.
"""
import os
import sys
import warnings

# Suppress TensorFlow/MediaPipe warnings BEFORE any imports
# These warnings are harmless but create poor user experience
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TF INFO and WARNING
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Suppress oneDNN messages
os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'  # Disable GPU (not available on Pi)

# Suppress Python warnings from absl (used by TensorFlow)
warnings.filterwarnings('ignore', category=UserWarning, module='absl')
warnings.filterwarnings('ignore', category=FutureWarning)

# Redirect stderr temporarily during MediaPipe import to suppress C++ warnings
# This handles the prctl and inference_feedback_manager warnings
import io
_stderr = sys.stderr
sys.stderr = io.StringIO()

from app import create_app
from app.extensions import socketio

# Restore stderr after imports
sys.stderr = _stderr

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
