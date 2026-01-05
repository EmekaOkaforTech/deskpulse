"""DeskPulse Windows Desktop Client - Configuration Management."""
import os
import json
import logging
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Optional

logger = logging.getLogger('deskpulse.windows.config')

# Default configuration
DEFAULT_CONFIG = {
    "backend_url": "http://raspberrypi.local:5000",
    "version": "1.0.0"
}

# Track last modification time for config change detection
_last_config_mtime: Optional[float] = None


def get_config_path() -> Path:
    """
    Get the configuration file path.

    Returns %APPDATA%/DeskPulse/config.json on Windows.
    Falls back to %TEMP%/DeskPulse/config.json if %APPDATA% is not writable.

    Returns:
        Path: Configuration file path
    """
    # Try APPDATA first (standard location)
    appdata = os.getenv('APPDATA')
    if appdata:
        config_dir = Path(appdata) / 'DeskPulse'
        try:
            config_dir.mkdir(parents=True, exist_ok=True)
            # Test write permissions
            test_file = config_dir / '.write_test'
            test_file.touch()
            test_file.unlink()
            logger.info(f"Using config directory: {config_dir}")
            return config_dir / 'config.json'
        except (OSError, PermissionError) as e:
            logger.warning(f"APPDATA directory not writable: {e}, falling back to TEMP")

    # Fall back to TEMP (corporate IT restrictions)
    temp_dir = Path(os.getenv('TEMP', '/tmp')) / 'DeskPulse'
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.warning(f"Using fallback config directory: {temp_dir}")
    return temp_dir / 'config.json'


def validate_backend_url(url: str) -> str:
    """
    Validate backend URL for security (local network only).

    Privacy requirement NFR-S1: Only allow local network URLs.

    Args:
        url: Backend URL to validate

    Returns:
        str: Validated URL

    Raises:
        ValueError: If URL is invalid or external
    """
    parsed = urlparse(url)

    # Protocol check
    if parsed.scheme not in ['http', 'https']:
        raise ValueError(f"Invalid protocol: Use http or https (got: {parsed.scheme})")

    # Hostname check
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Missing hostname in URL")

    # Local network patterns (privacy requirement NFR-S1)
    local_patterns = [
        r'^localhost$',
        r'^127\.\d+\.\d+\.\d+$',          # 127.x.x.x
        r'^192\.168\.\d+\.\d+$',          # 192.168.x.x
        r'^10\.\d+\.\d+\.\d+$',           # 10.x.x.x
        r'^172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+$',  # 172.16-31.x.x
        r'^.*\.local$'                    # mDNS (e.g., raspberrypi.local)
    ]

    if not any(re.match(pattern, hostname) for pattern in local_patterns):
        raise ValueError(
            f"External URLs not allowed (privacy requirement): {hostname}\n"
            f"Allowed: localhost, 127.x.x.x, 192.168.x.x, 10.x.x.x, 172.16-31.x.x, *.local"
        )

    logger.info(f"Backend URL validated: {url}")
    return url


def load_config() -> Dict:
    """
    Load configuration from file.

    - Loads from config path
    - Validates JSON format (recreates if corrupted)
    - Validates backend_url
    - Returns defaults if missing

    Returns:
        dict: Configuration dictionary
    """
    global _last_config_mtime

    config_path = get_config_path()

    # If config doesn't exist, create with defaults
    if not config_path.exists():
        logger.info("Config file not found, creating with defaults")
        save_config(DEFAULT_CONFIG)
        _last_config_mtime = config_path.stat().st_mtime
        return DEFAULT_CONFIG.copy()

    # Load and parse config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Validate backend_url
        if 'backend_url' in config:
            config['backend_url'] = validate_backend_url(config['backend_url'])
        else:
            logger.warning("backend_url missing from config, using default")
            config['backend_url'] = DEFAULT_CONFIG['backend_url']

        # Ensure version exists
        if 'version' not in config:
            config['version'] = DEFAULT_CONFIG['version']

        _last_config_mtime = config_path.stat().st_mtime
        logger.info(f"Config loaded successfully from {config_path}")
        return config

    except json.JSONDecodeError as e:
        logger.error(f"Corrupted config file (invalid JSON): {e}")
        logger.info("Recreating config with defaults")
        save_config(DEFAULT_CONFIG)
        _last_config_mtime = config_path.stat().st_mtime
        return DEFAULT_CONFIG.copy()

    except ValueError as e:
        # Backend URL validation failed
        logger.error(f"Invalid backend URL in config: {e}")
        raise

    except Exception as e:
        logger.exception(f"Error loading config: {e}")
        logger.info("Using defaults due to error")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save
    """
    global _last_config_mtime

    config_path = get_config_path()

    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate backend_url before saving
        if 'backend_url' in config:
            validate_backend_url(config['backend_url'])

        # Write config with pretty formatting
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        _last_config_mtime = config_path.stat().st_mtime
        logger.info(f"Config saved successfully to {config_path}")

    except Exception as e:
        logger.exception(f"Error saving config: {e}")
        raise


def watch_config_changes() -> bool:
    """
    Check if config file has been modified since last load.

    Returns:
        bool: True if config has been modified, False otherwise
    """
    global _last_config_mtime

    if _last_config_mtime is None:
        return False

    config_path = get_config_path()
    if not config_path.exists():
        return False

    try:
        current_mtime = config_path.stat().st_mtime
        return current_mtime > _last_config_mtime
    except Exception as e:
        logger.warning(f"Error checking config modification time: {e}")
        return False
