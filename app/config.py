"""
DeskPulse Configuration Module.

Configuration hierarchy (highest priority first):
1. Environment variables (for secrets only)
2. User config: ~/.config/deskpulse/config.ini
3. System config: /etc/deskpulse/config.ini
4. Hardcoded defaults in Config class

This module follows the XDG Base Directory specification for Linux.
"""
import configparser
import logging
import os

# Define config paths as module-level constants (enables test mocking)
SYSTEM_CONFIG_PATH = "/etc/deskpulse/config.ini"
USER_CONFIG_PATH = os.path.expanduser("~/.config/deskpulse/config.ini")

# Module-level config parser - loaded once at import time
_config = configparser.ConfigParser()
_config.read([SYSTEM_CONFIG_PATH, USER_CONFIG_PATH])


def get_ini_value(section: str, key: str, fallback: str) -> str:
    """
    Get configuration value from INI files with fallback.

    Reads from the parsed INI configuration. If the section or key
    doesn't exist, returns the fallback value.

    Args:
        section: INI section name (e.g., 'camera')
        key: Configuration key (e.g., 'device')
        fallback: Default value if not found

    Returns:
        Configuration value as string
    """
    try:
        return _config.get(section, key, fallback=fallback)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return fallback


def get_ini_int(section: str, key: str, fallback: int) -> int:
    """
    Get integer configuration value from INI files with fallback.

    Args:
        section: INI section name
        key: Configuration key
        fallback: Default integer value if not found or invalid

    Returns:
        Configuration value as integer
    """
    str_value = get_ini_value(section, key, str(fallback))
    try:
        return int(str_value)
    except ValueError:
        logging.error(
            f"Invalid {section}.{key} in config.ini - must be integer, "
            f"using fallback {fallback}"
        )
        return fallback


def get_ini_bool(section: str, key: str, fallback: bool) -> bool:
    """
    Get boolean configuration value from INI files with fallback.

    Recognizes: true/false, yes/no, 1/0, on/off (case-insensitive)

    Args:
        section: INI section name
        key: Configuration key
        fallback: Default boolean value if not found or invalid

    Returns:
        Configuration value as boolean
    """
    str_value = get_ini_value(section, key, str(fallback)).lower()
    if str_value in ("true", "yes", "1", "on"):
        return True
    elif str_value in ("false", "no", "0", "off"):
        return False
    else:
        logging.error(
            f"Invalid {section}.{key} in config.ini - must be boolean, "
            f"using fallback {fallback}"
        )
        return fallback


def get_ini_float(section: str, key: str, fallback: float) -> float:
    """
    Get float configuration value from INI files with fallback.

    Args:
        section: INI section name
        key: Configuration key
        fallback: Default float value if not found or invalid

    Returns:
        Configuration value as float
    """
    str_value = get_ini_value(section, key, str(fallback))
    try:
        return float(str_value)
    except ValueError:
        logging.warning(
            f"Invalid float value for [{section}] {key}='{str_value}', "
            f"using fallback {fallback}"
        )
        return fallback


def validate_config() -> dict:
    """
    Validate configuration values and return validated dict with logging.

    Validates all configuration options and logs warnings for non-critical
    issues and errors for critical issues. Returns validated configuration
    with fallback values applied where needed.

    Returns:
        Dictionary with validated configuration values
    """
    validated = {}

    # Camera device validation (0-9)
    camera_device = get_ini_int("camera", "device", 0)
    if not 0 <= camera_device <= 9:
        logging.error(
            f"Camera device {camera_device} out of range (0-9), using fallback 0"
        )
        camera_device = 0
    # Optional: warn if camera doesn't exist (may not be connected yet)
    camera_path = f"/dev/video{camera_device}"
    if not os.path.exists(camera_path):
        logging.warning(f"Camera device {camera_device} not found at {camera_path}")
    validated["camera_device"] = camera_device

    # Camera resolution
    resolution = get_ini_value("camera", "resolution", "720p")
    if resolution not in ("480p", "720p", "1080p"):
        logging.warning(
            f"Unknown resolution '{resolution}', valid values: 480p, 720p, 1080p"
        )
    validated["camera_resolution"] = resolution

    # Camera FPS target
    fps_target = get_ini_int("camera", "fps_target", 10)
    if not 1 <= fps_target <= 60:
        logging.warning(f"FPS target {fps_target} outside recommended range (1-60)")
    validated["camera_fps_target"] = fps_target

    # Alert threshold (1-60 minutes)
    threshold_minutes = get_ini_int("alerts", "posture_threshold_minutes", 10)
    if not 1 <= threshold_minutes <= 60:
        logging.error(
            f"Threshold {threshold_minutes} out of range (1-60), using fallback 10"
        )
        threshold_minutes = 10
    validated["alert_threshold"] = threshold_minutes * 60  # Convert to seconds

    # Alert cooldown (1-30 minutes) - Story 3.1
    cooldown_minutes = get_ini_int("alerts", "alert_cooldown_minutes", 5)
    if not 1 <= cooldown_minutes <= 30:
        logging.error(
            f"Alert cooldown {cooldown_minutes} out of range (1-30), using fallback 5"
        )
        cooldown_minutes = 5
    validated["alert_cooldown"] = cooldown_minutes * 60  # Convert to seconds

    # Notification enabled
    validated["notification_enabled"] = get_ini_bool(
        "alerts", "notification_enabled", True
    )

    # Dashboard port (1024-65535)
    port = get_ini_int("dashboard", "port", 5000)
    if not 1024 <= port <= 65535:
        logging.error(f"Port {port} out of range (1024-65535), using fallback 5000")
        port = 5000
    validated["dashboard_port"] = port

    # Dashboard update interval (1-10 seconds)
    update_interval = get_ini_int("dashboard", "update_interval_seconds", 2)
    if not 1 <= update_interval <= 10:
        logging.warning(
            f"Update interval {update_interval} outside recommended range (1-10)"
        )
    validated["dashboard_update_interval"] = update_interval

    return validated


class Config:
    """Base configuration class with INI file support."""

    # Camera settings from INI
    CAMERA_DEVICE = get_ini_int("camera", "device", 0)
    CAMERA_RESOLUTION = get_ini_value("camera", "resolution", "720p")
    CAMERA_FPS_TARGET = get_ini_int("camera", "fps_target", 10)

    # MediaPipe Pose Configuration (Story 2.2)
    MEDIAPIPE_MODEL_COMPLEXITY = get_ini_int("mediapipe", "model_complexity", 1)
    MEDIAPIPE_MIN_DETECTION_CONFIDENCE = get_ini_float(
        "mediapipe", "min_detection_confidence", 0.5
    )
    MEDIAPIPE_MIN_TRACKING_CONFIDENCE = get_ini_float(
        "mediapipe", "min_tracking_confidence", 0.5
    )
    MEDIAPIPE_SMOOTH_LANDMARKS = get_ini_bool("mediapipe", "smooth_landmarks", True)

    # Posture Classification Configuration (Story 2.3)
    POSTURE_ANGLE_THRESHOLD = get_ini_int("posture", "angle_threshold", 15)

    # Alert settings from INI (Story 1.3 + Story 3.1)
    ALERT_THRESHOLD = get_ini_int("alerts", "posture_threshold_minutes", 10) * 60
    ALERT_COOLDOWN = get_ini_int("alerts", "alert_cooldown_minutes", 5) * 60  # Story 3.1
    NOTIFICATION_ENABLED = get_ini_bool("alerts", "notification_enabled", True)

    # Dashboard settings from INI
    DASHBOARD_PORT = get_ini_int("dashboard", "port", 5000)
    DASHBOARD_UPDATE_INTERVAL = get_ini_int("dashboard", "update_interval_seconds", 2)

    # CORS allowed origins - configurable via INI or defaults to localhost
    # Can be comma-separated list in INI: cors_origins = http://localhost:5000,http://pi.local:5000
    _cors_origins_str = get_ini_value("dashboard", "cors_origins", "")
    CORS_ALLOWED_ORIGINS = (
        [o.strip() for o in _cors_origins_str.split(",") if o.strip()]
        if _cors_origins_str
        else [
            "http://localhost:5000",
            "http://127.0.0.1:5000",
            "http://raspberrypi.local:5000",
        ]
    )

    # PRESERVED from Story 1.1 - Network binding (NFR-S2)
    # Read from config.ini [dashboard] section, fallback to 127.0.0.1 (secure default)
    HOST = get_ini_value("dashboard", "host", "127.0.0.1")
    PORT = get_ini_int("dashboard", "port", 5000)

    # Database path (from Story 1.1/1.2)
    DATABASE_PATH = os.path.join(os.getcwd(), "data", "deskpulse.db")

    # Secrets ALWAYS from environment variables, NEVER from INI
    # Uses DESKPULSE_SECRET_KEY (preferred) or SECRET_KEY (legacy)
    # WARNING: Insecure default only for development - production MUST set env var
    _secret = os.environ.get("DESKPULSE_SECRET_KEY") or os.environ.get("SECRET_KEY")
    SECRET_KEY = _secret if _secret else "dev-key-change-in-production"

    # Legacy alias for backward compatibility with Story 1.1
    POSTURE_ALERT_THRESHOLD = ALERT_THRESHOLD


class DevelopmentConfig(Config):
    """Development configuration with debug enabled."""

    DEBUG = True
    LOG_LEVEL = "DEBUG"
    MOCK_CAMERA = False
    # Inherit HOST from base Config (reads from config.ini)


class TestingConfig(Config):
    """
    Testing configuration with hardcoded values.

    TestingConfig bypasses INI file loading to ensure deterministic tests.
    All values are hardcoded - tests should NOT depend on INI files.
    """

    TESTING = True
    DATABASE_PATH = ":memory:"
    MOCK_CAMERA = True

    # Override INI-loaded values with hardcoded test values
    CAMERA_DEVICE = 0
    CAMERA_RESOLUTION = "720p"
    CAMERA_FPS_TARGET = 10
    POSTURE_ANGLE_THRESHOLD = 15  # Posture classification threshold (Story 2.3)
    ALERT_THRESHOLD = 600  # 10 minutes
    ALERT_COOLDOWN = 300  # 5 minutes (Story 3.1)
    NOTIFICATION_ENABLED = True
    DASHBOARD_PORT = 5000
    DASHBOARD_UPDATE_INTERVAL = 2
    POSTURE_ALERT_THRESHOLD = 600
    SECRET_KEY = "test-secret-key"
    CORS_ALLOWED_ORIGINS = ["http://localhost:5000", "http://127.0.0.1:5000"]


class ProductionConfig(Config):
    """Production configuration with logging."""

    DEBUG = False
    LOG_LEVEL = "INFO"

    def __init__(self):
        """Validate production configuration on instantiation."""
        if self.SECRET_KEY == "dev-key-change-in-production":
            raise ValueError(
                "SECURITY ERROR: SECRET_KEY not set. "
                "Set DESKPULSE_SECRET_KEY environment variable for production."
            )


class SystemdConfig(ProductionConfig):
    """Configuration for systemd service deployment."""

    LOG_LEVEL = "WARNING"
    # For systemd deployment on Pi, bind to local network interface
    # Set to Pi's local IP or use environment variable for specific interface
    HOST = os.environ.get("FLASK_HOST") or "127.0.0.1"
