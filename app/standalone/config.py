"""
Windows Configuration Module for Standalone Edition.

Handles Windows-specific paths, configuration, and settings.
Uses %APPDATA%/DeskPulse for all data storage.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger('deskpulse.standalone.config')


def get_appdata_dir() -> Path:
    """
    Get DeskPulse data directory in Windows %APPDATA%.

    Returns:
        Path: %APPDATA%/DeskPulse (e.g., C:/Users/John/AppData/Roaming/DeskPulse)

    Creates directory if it doesn't exist.
    """
    appdata = os.getenv('APPDATA')
    if not appdata:
        # Fallback to %USERPROFILE%/AppData/Roaming
        userprofile = os.getenv('USERPROFILE', 'C:/Users/Default')
        appdata = os.path.join(userprofile, 'AppData', 'Roaming')

    deskpulse_dir = Path(appdata) / 'DeskPulse'
    deskpulse_dir.mkdir(parents=True, exist_ok=True)

    return deskpulse_dir


def get_config_path() -> Path:
    """Get path to config.json file."""
    return get_appdata_dir() / 'config.json'


def get_database_path() -> Path:
    """Get path to SQLite database file."""
    return get_appdata_dir() / 'deskpulse.db'


def get_log_dir() -> Path:
    """
    Get log directory path.

    Returns:
        Path: %APPDATA%/DeskPulse/logs
    """
    log_dir = get_appdata_dir() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_path() -> Path:
    """Get path to main log file."""
    return get_log_dir() / 'deskpulse.log'


DEFAULT_CONFIG = {
    'camera': {
        'index': 0,  # Default camera index
        'fps': 10,   # Frames per second
        'width': 640,
        'height': 480,
        'backend': 'directshow'  # Windows camera backend
    },
    'monitoring': {
        'alert_threshold_seconds': 600,  # 10 minutes
        'detection_interval_seconds': 1,
        'enable_notifications': True
    },
    'analytics': {
        'history_days': 30,  # Pro: 30 days
        'enable_exports': True
    },
    'ui': {
        'start_minimized': False,
        'show_dashboard_on_start': False,
        'enable_toast_notifications': True
    },
    'advanced': {
        'log_level': 'INFO',
        'enable_debug': False,
        'camera_warmup_seconds': 2
    }
}


def load_config() -> Dict[str, Any]:
    """
    Load configuration from file.

    Returns:
        dict: Configuration dictionary

    If config file doesn't exist, creates it with defaults.
    """
    config_path = get_config_path()

    if not config_path.exists():
        logger.info(f"Config file not found, creating with defaults: {config_path}")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Merge with defaults (in case new keys added)
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)

        logger.info(f"Config loaded from: {config_path}")
        return merged

    except Exception as e:
        logger.error(f"Failed to load config, using defaults: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary

    Returns:
        bool: True if successful, False otherwise
    """
    config_path = get_config_path()

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Config saved to: {config_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def get_camera_index() -> int:
    """Get configured camera index."""
    config = load_config()
    return config.get('camera', {}).get('index', 0)


def get_camera_fps() -> int:
    """Get configured camera FPS."""
    config = load_config()
    return config.get('camera', {}).get('fps', 10)


def get_alert_threshold() -> int:
    """Get alert threshold in seconds."""
    config = load_config()
    return config.get('monitoring', {}).get('alert_threshold_seconds', 600)


def is_notifications_enabled() -> bool:
    """Check if notifications are enabled."""
    config = load_config()
    return config.get('monitoring', {}).get('enable_notifications', True)


def get_history_days() -> int:
    """Get number of days to keep history."""
    config = load_config()
    return config.get('analytics', {}).get('history_days', 30)


def setup_logging():
    """
    Configure logging for standalone Windows edition.

    Logs to:
    - File: %APPDATA%/DeskPulse/logs/deskpulse.log (rotating, 10 MB, 5 backups)
    - Console: DEBUG level for development
    """
    from logging.handlers import RotatingFileHandler

    log_file = get_log_path()
    config = load_config()
    log_level = config.get('advanced', {}).get('log_level', 'INFO')

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler (for development/debugging)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"Logging configured: {log_file} (level: {log_level})")
    logger.info(f"DeskPulse Standalone v{__version__} starting")
    logger.info(f"Data directory: {get_appdata_dir()}")


if __name__ == '__main__':
    # Test configuration
    setup_logging()

    print(f"AppData Directory: {get_appdata_dir()}")
    print(f"Config Path: {get_config_path()}")
    print(f"Database Path: {get_database_path()}")
    print(f"Log Path: {get_log_path()}")

    print("\nLoading config...")
    config = load_config()
    print(json.dumps(config, indent=2))

    print("\nConfig loaded successfully!")
