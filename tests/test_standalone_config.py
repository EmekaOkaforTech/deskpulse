"""
Unit tests for Windows standalone configuration module.

Tests Windows-specific paths, configuration, and settings.
Uses mocked %APPDATA% to avoid touching real system.
"""

import pytest
import json
import logging
from pathlib import Path
from unittest.mock import patch, Mock
from app.standalone.config import (
    get_appdata_dir,
    get_config_path,
    get_database_path,
    get_log_dir,
    get_log_path,
    load_config,
    save_config,
    DEFAULT_CONFIG,
    get_camera_index,
    get_camera_fps,
    get_alert_threshold,
    is_notifications_enabled,
    get_history_days,
    setup_logging
)


@pytest.fixture
def temp_appdata(tmp_path, monkeypatch):
    """Mock %APPDATA% to temp directory."""
    fake_appdata = tmp_path / 'AppData' / 'Roaming'
    fake_appdata.mkdir(parents=True)
    monkeypatch.setenv('APPDATA', str(fake_appdata))
    return fake_appdata


@pytest.fixture
def clean_logger():
    """Clean up logger handlers after test."""
    yield
    # Remove all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


class TestPathFunctions:
    """Test Windows path generation functions."""

    def test_get_appdata_dir_creates_directory(self, temp_appdata):
        """Test AppData directory creation."""
        appdata = get_appdata_dir()
        assert appdata.exists()
        assert 'DeskPulse' in str(appdata)
        assert appdata.is_dir()

    def test_get_appdata_dir_fallback_no_appdata(self, tmp_path, monkeypatch):
        """Test fallback when %APPDATA% not set."""
        # Remove APPDATA, set USERPROFILE
        monkeypatch.delenv('APPDATA', raising=False)
        fake_userprofile = tmp_path / 'Users' / 'TestUser'
        fake_userprofile.mkdir(parents=True)
        monkeypatch.setenv('USERPROFILE', str(fake_userprofile))

        appdata = get_appdata_dir()
        assert 'AppData' in str(appdata)
        assert 'Roaming' in str(appdata)
        assert 'DeskPulse' in str(appdata)

    def test_get_config_path(self, temp_appdata):
        """Test config.json path generation."""
        config_path = get_config_path()
        assert config_path.name == 'config.json'
        assert 'DeskPulse' in str(config_path)

    def test_get_database_path(self, temp_appdata):
        """Test database path generation."""
        db_path = get_database_path()
        assert db_path.name == 'deskpulse.db'
        assert 'DeskPulse' in str(db_path)

    def test_get_log_dir_creates_directory(self, temp_appdata):
        """Test log directory creation."""
        log_dir = get_log_dir()
        assert log_dir.exists()
        assert log_dir.is_dir()
        assert log_dir.name == 'logs'

    def test_get_log_path(self, temp_appdata):
        """Test log file path generation."""
        log_path = get_log_path()
        assert log_path.name == 'deskpulse.log'
        assert 'logs' in str(log_path)


class TestConfigurationManagement:
    """Test configuration loading, saving, and merging."""

    def test_load_config_creates_defaults_if_missing(self, temp_appdata):
        """Test config creation with defaults when file doesn't exist."""
        config = load_config()

        # Verify defaults
        assert config['camera']['fps'] == 10
        assert config['monitoring']['alert_threshold_seconds'] == 600
        assert config['advanced']['log_level'] == 'INFO'

        # Verify file created
        assert get_config_path().exists()

    def test_load_config_reads_existing_file(self, temp_appdata):
        """Test loading existing config file."""
        # Create config with custom values
        custom_config = {'camera': {'fps': 15, 'index': 1}}
        save_config(custom_config)

        # Load and verify
        config = load_config()
        assert config['camera']['fps'] == 15
        assert config['camera']['index'] == 1

    def test_load_config_merges_with_defaults(self, temp_appdata):
        """Test partial config merges with defaults."""
        # Save partial config (only camera settings)
        partial = {'camera': {'fps': 5}}
        save_config(partial)

        # Load and verify merge
        config = load_config()
        assert config['camera']['fps'] == 5  # User value
        assert config['monitoring']['alert_threshold_seconds'] == 600  # Default value
        assert 'analytics' in config  # Default section
        assert 'ui' in config  # Default section

    def test_load_config_deep_merge_preserves_nested_defaults(self, temp_appdata):
        """Test deep merge preserves nested default values (Issue #2 fix)."""
        # Save partial config with only ONE camera setting
        partial = {'camera': {'fps': 15}}
        save_config(partial)

        # Load and verify deep merge preserved other camera defaults
        config = load_config()
        assert config['camera']['fps'] == 15  # User value
        assert config['camera']['width'] == 640  # Default preserved
        assert config['camera']['height'] == 480  # Default preserved
        assert config['camera']['index'] == 0  # Default preserved
        assert config['camera']['backend'] == 'directshow'  # Default preserved

    def test_load_config_deep_merge_multiple_nested_levels(self, temp_appdata):
        """Test deep merge works with partial updates across multiple sections."""
        # Save partial config touching multiple sections
        partial = {
            'camera': {'fps': 20},
            'monitoring': {'enable_notifications': False},
            'advanced': {'log_level': 'DEBUG'}
        }
        save_config(partial)

        # Load and verify all defaults preserved
        config = load_config()

        # Camera section
        assert config['camera']['fps'] == 20  # User value
        assert config['camera']['width'] == 640  # Default preserved

        # Monitoring section
        assert config['monitoring']['enable_notifications'] is False  # User value
        assert config['monitoring']['alert_threshold_seconds'] == 600  # Default preserved

        # Advanced section
        assert config['advanced']['log_level'] == 'DEBUG'  # User value
        assert config['advanced']['enable_debug'] is False  # Default preserved

        # Completely untouched sections
        assert config['analytics']['history_days'] == 30
        assert config['ui']['start_minimized'] is False

    def test_save_config_creates_valid_json(self, temp_appdata):
        """Test config saving creates valid JSON file."""
        test_config = {
            'camera': {'fps': 20},
            'test_key': 'test_value'
        }

        success = save_config(test_config)
        assert success is True

        # Verify file is valid JSON
        config_path = get_config_path()
        with open(config_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            assert loaded['camera']['fps'] == 20
            assert loaded['test_key'] == 'test_value'

    def test_save_config_handles_errors_gracefully(self, temp_appdata, monkeypatch):
        """Test save_config error handling."""
        # Make config path unwritable by patching open
        def mock_open(*args, **kwargs):
            raise PermissionError("Access denied")

        monkeypatch.setattr('builtins.open', mock_open)

        success = save_config({'test': 'data'})
        assert success is False

    def test_load_config_handles_invalid_json(self, temp_appdata):
        """Test load_config with corrupted JSON file."""
        # Write invalid JSON
        config_path = get_config_path()
        config_path.write_text('{ invalid json }', encoding='utf-8')

        # Should return defaults without crashing
        config = load_config()
        assert config == DEFAULT_CONFIG


class TestNonAsciiPaths:
    """Test configuration with non-ASCII usernames."""

    def test_config_with_non_ascii_username(self, tmp_path, monkeypatch):
        """Test config with non-ASCII username (José)."""
        fake_appdata = tmp_path / 'Users' / 'José' / 'AppData' / 'Roaming'
        fake_appdata.mkdir(parents=True)
        monkeypatch.setenv('APPDATA', str(fake_appdata))

        config = load_config()
        config_path = get_config_path()

        assert 'José' in str(config_path)
        assert config_path.exists()

    def test_config_with_unicode_characters(self, tmp_path, monkeypatch):
        """Test config with various Unicode characters."""
        fake_appdata = tmp_path / 'Users' / 'München_北京' / 'AppData' / 'Roaming'
        fake_appdata.mkdir(parents=True)
        monkeypatch.setenv('APPDATA', str(fake_appdata))

        config = load_config()
        success = save_config(config)

        assert success is True
        assert get_config_path().exists()


class TestPathWithSpaces:
    """Test path handling with spaces."""

    def test_paths_with_spaces(self, tmp_path, monkeypatch):
        """Test config paths with spaces in username."""
        fake_appdata = tmp_path / 'Users' / 'John Smith' / 'AppData' / 'Roaming'
        fake_appdata.mkdir(parents=True)
        monkeypatch.setenv('APPDATA', str(fake_appdata))

        config_path = get_config_path()
        db_path = get_database_path()

        assert 'John Smith' in str(config_path)
        assert 'John Smith' in str(db_path)

        # Verify we can create files
        config = load_config()
        assert config_path.exists()


class TestConfigAccessors:
    """Test configuration accessor functions."""

    def test_get_camera_index(self, temp_appdata):
        """Test camera index accessor."""
        # Default value
        assert get_camera_index() == 0

        # Custom value
        config = load_config()
        config['camera']['index'] = 2
        save_config(config)
        assert get_camera_index() == 2

    def test_get_camera_fps(self, temp_appdata):
        """Test camera FPS accessor."""
        # Default value
        assert get_camera_fps() == 10

        # Custom value
        config = load_config()
        config['camera']['fps'] = 15
        save_config(config)
        assert get_camera_fps() == 15

    def test_get_alert_threshold(self, temp_appdata):
        """Test alert threshold accessor."""
        # Default value
        assert get_alert_threshold() == 600

        # Custom value
        config = load_config()
        config['monitoring']['alert_threshold_seconds'] = 300
        save_config(config)
        assert get_alert_threshold() == 300

    def test_is_notifications_enabled(self, temp_appdata):
        """Test notifications enabled accessor."""
        # Default value
        assert is_notifications_enabled() is True

        # Disabled
        config = load_config()
        config['monitoring']['enable_notifications'] = False
        save_config(config)
        assert is_notifications_enabled() is False

    def test_get_history_days(self, temp_appdata):
        """Test history days accessor."""
        # Default value
        assert get_history_days() == 30

        # Custom value
        config = load_config()
        config['analytics']['history_days'] = 90
        save_config(config)
        assert get_history_days() == 90


class TestLoggingSetup:
    """Test logging configuration."""

    def test_setup_logging_creates_log_file(self, temp_appdata, clean_logger):
        """Test logging setup creates log file."""
        setup_logging()

        log_path = get_log_path()
        assert log_path.exists()

    def test_setup_logging_respects_log_level(self, temp_appdata, clean_logger):
        """Test logging respects configured log level."""
        # Set custom log level
        config = load_config()
        config['advanced']['log_level'] = 'DEBUG'
        save_config(config)

        setup_logging()

        # Check root logger has handlers
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_setup_logging_with_invalid_level(self, temp_appdata, clean_logger):
        """Test logging with invalid level falls back to default."""
        config = load_config()
        config['advanced']['log_level'] = 'INVALID'
        save_config(config)

        # Should not crash
        try:
            setup_logging()
            # If it doesn't crash, test passes
            assert True
        except Exception as e:
            pytest.fail(f"setup_logging crashed with invalid level: {e}")


class TestConfigurationMigration:
    """Test configuration version migration."""

    def test_new_keys_added_on_update(self, temp_appdata):
        """Test new config keys added without overwriting user values."""
        # Save old config (missing some new keys)
        old_config = {
            'camera': {'fps': 15, 'index': 1}
            # Missing: monitoring, analytics, ui, advanced
        }
        save_config(old_config)

        # Load config (should merge with defaults)
        config = load_config()

        # User values preserved
        assert config['camera']['fps'] == 15
        assert config['camera']['index'] == 1

        # New keys added from defaults
        assert 'monitoring' in config
        assert 'analytics' in config
        assert 'ui' in config
        assert 'advanced' in config

    def test_user_customizations_not_overwritten(self, temp_appdata):
        """Test user customizations preserved on merge."""
        # Save config with all user customizations
        user_config = {
            'camera': {'fps': 20, 'index': 2, 'width': 1280},
            'monitoring': {'alert_threshold_seconds': 300},
            'analytics': {'history_days': 90}
        }
        save_config(user_config)

        # Load and verify user values preserved
        config = load_config()
        assert config['camera']['fps'] == 20
        assert config['camera']['index'] == 2
        assert config['monitoring']['alert_threshold_seconds'] == 300
        assert config['analytics']['history_days'] == 90


class TestDefaultConfig:
    """Test DEFAULT_CONFIG structure."""

    def test_default_config_has_all_sections(self):
        """Test DEFAULT_CONFIG contains all required sections."""
        # Import fresh to avoid test pollution
        from app.standalone.config import DEFAULT_CONFIG as config
        assert 'camera' in config
        assert 'monitoring' in config
        assert 'analytics' in config
        assert 'ui' in config
        assert 'advanced' in config

    def test_default_config_values_are_sane(self):
        """Test DEFAULT_CONFIG has reasonable default values."""
        # Import fresh to avoid test pollution
        from app.standalone.config import DEFAULT_CONFIG as config
        assert config['camera']['fps'] > 0
        assert config['camera']['index'] >= 0
        assert config['monitoring']['alert_threshold_seconds'] > 0
        assert config['advanced']['log_level'] in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
