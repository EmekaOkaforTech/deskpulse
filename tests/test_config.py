"""
Tests for DeskPulse Configuration Module.

Tests cover:
- INI file loading from system and user paths
- User config override behavior
- Fallback values when INI files missing
- Type conversion (int, bool, string)
- Invalid value handling
- Secret key from environment only
- TestingConfig isolation from INI files
- Flask app integration
"""
import pytest
from importlib import reload


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directories."""
    system_dir = tmp_path / "etc" / "deskpulse"
    system_dir.mkdir(parents=True)

    user_dir = tmp_path / "home" / ".config" / "deskpulse"
    user_dir.mkdir(parents=True)

    return {
        "system": system_dir,
        "user": user_dir,
        "system_config": system_dir / "config.ini",
        "user_config": user_dir / "config.ini",
    }


@pytest.fixture
def mock_env(monkeypatch):
    """Clear and mock environment variables."""
    monkeypatch.delenv("DESKPULSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    return monkeypatch


@pytest.fixture
def reload_config(monkeypatch):
    """Helper to reload config module with patched paths."""

    def _reload(system_path=None, user_path=None):
        import app.config as config_module

        if system_path is not None:
            monkeypatch.setattr(config_module, "SYSTEM_CONFIG_PATH", str(system_path))
        if user_path is not None:
            monkeypatch.setattr(config_module, "USER_CONFIG_PATH", str(user_path))

        # Reset the configparser and reload
        config_module._config = __import__("configparser").ConfigParser()
        paths = []
        if system_path:
            paths.append(str(system_path))
        if user_path:
            paths.append(str(user_path))
        config_module._config.read(paths)

        return config_module

    return _reload


class TestINILoading:
    """Tests for INI file loading functionality."""

    def test_system_config_loading(self, temp_config_dir, reload_config):
        """Verify system config file is loaded correctly."""
        system_ini = temp_config_dir["system_config"]
        system_ini.write_text("[camera]\ndevice = 3\n")

        config_module = reload_config(
            system_path=system_ini, user_path=temp_config_dir["user_config"]
        )

        result = config_module.get_ini_int("camera", "device", 0)
        assert result == 3

    def test_user_config_loading(self, temp_config_dir, reload_config):
        """Verify user config file is loaded correctly."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\ndevice = 5\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.get_ini_int("camera", "device", 0)
        assert result == 5

    def test_user_override_takes_precedence(self, temp_config_dir, reload_config):
        """User config should override system config."""
        system_ini = temp_config_dir["system_config"]
        system_ini.write_text("[camera]\ndevice = 0\n")

        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\ndevice = 1\n")

        config_module = reload_config(system_path=system_ini, user_path=user_ini)

        result = config_module.get_ini_int("camera", "device", 99)
        assert result == 1

    def test_fallback_values_when_ini_missing(self, temp_config_dir, reload_config):
        """Config should use fallbacks when INI files don't exist."""
        # Point to non-existent files
        config_module = reload_config(
            system_path=temp_config_dir["system"] / "nonexistent.ini",
            user_path=temp_config_dir["user"] / "nonexistent.ini",
        )

        # Should use fallback values
        assert config_module.get_ini_int("camera", "device", 0) == 0
        assert config_module.get_ini_value("camera", "resolution", "720p") == "720p"
        assert config_module.get_ini_bool("alerts", "notification_enabled", True)

    def test_partial_config_uses_fallbacks(self, temp_config_dir, reload_config):
        """Missing sections/keys should use fallbacks."""
        system_ini = temp_config_dir["system_config"]
        system_ini.write_text("[camera]\ndevice = 2\n")  # Only camera section

        config_module = reload_config(
            system_path=system_ini, user_path=temp_config_dir["user_config"]
        )

        # camera.device is set
        assert config_module.get_ini_int("camera", "device", 0) == 2
        # alerts.posture_threshold_minutes uses fallback
        assert (
            config_module.get_ini_int("alerts", "posture_threshold_minutes", 10) == 10
        )

    def test_get_ini_value_exception_handling(self, temp_config_dir, reload_config):
        """get_ini_value should handle exceptions gracefully."""
        import configparser

        config_module = reload_config(
            system_path=temp_config_dir["system_config"],
            user_path=temp_config_dir["user_config"],
        )

        # Manually corrupt the config parser to trigger exception path
        original_get = config_module._config.get

        def raise_exception(*args, **kwargs):
            raise configparser.NoSectionError("test")

        config_module._config.get = raise_exception

        # Should return fallback when exception occurs
        result = config_module.get_ini_value("nonexistent", "key", "fallback_value")
        assert result == "fallback_value"

        # Restore original
        config_module._config.get = original_get


class TestValueParsing:
    """Tests for value type conversion."""

    def test_integer_parsing(self, temp_config_dir, reload_config):
        """Integer values should be parsed correctly."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\ndevice = 7\nfps_target = 15\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        assert config_module.get_ini_int("camera", "device", 0) == 7
        assert config_module.get_ini_int("camera", "fps_target", 10) == 15

    def test_invalid_integer_uses_fallback(
        self, temp_config_dir, reload_config, caplog
    ):
        """Invalid integer values should log error and use fallback."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\ndevice = abc\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.get_ini_int("camera", "device", 0)
        assert result == 0
        assert "must be integer" in caplog.text

    def test_boolean_parsing_true_values(self, temp_config_dir, reload_config):
        """Boolean true values should be recognized."""
        for value in ["true", "True", "TRUE", "yes", "YES", "1", "on", "ON"]:
            user_ini = temp_config_dir["user_config"]
            user_ini.write_text(f"[alerts]\nnotification_enabled = {value}\n")

            config_module = reload_config(
                system_path=temp_config_dir["system_config"], user_path=user_ini
            )

            assert config_module.get_ini_bool(
                "alerts", "notification_enabled", False
            ), f"Failed for value: {value}"

    def test_boolean_parsing_false_values(self, temp_config_dir, reload_config):
        """Boolean false values should be recognized."""
        for value in ["false", "False", "FALSE", "no", "NO", "0", "off", "OFF"]:
            user_ini = temp_config_dir["user_config"]
            user_ini.write_text(f"[alerts]\nnotification_enabled = {value}\n")

            config_module = reload_config(
                system_path=temp_config_dir["system_config"], user_path=user_ini
            )

            assert not config_module.get_ini_bool(
                "alerts", "notification_enabled", True
            ), f"Failed for value: {value}"

    def test_invalid_boolean_uses_fallback(
        self, temp_config_dir, reload_config, caplog
    ):
        """Invalid boolean values should log error and use fallback."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[alerts]\nnotification_enabled = maybe\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.get_ini_bool("alerts", "notification_enabled", True)
        assert result is True
        assert "must be boolean" in caplog.text

    def test_string_parsing(self, temp_config_dir, reload_config):
        """String values should be returned as-is."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\nresolution = 1080p\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        assert config_module.get_ini_value("camera", "resolution", "720p") == "1080p"


class TestSecretHandling:
    """Tests for secret key handling."""

    def test_secret_key_from_environment(self, mock_env):
        """SECRET_KEY must come from environment variable."""
        mock_env.setenv("DESKPULSE_SECRET_KEY", "test-secret-key-12345")

        import app.config as config_module

        reload(config_module)

        assert config_module.Config.SECRET_KEY == "test-secret-key-12345"

    def test_secret_key_legacy_fallback(self, mock_env):
        """SECRET_KEY should fallback to legacy SECRET_KEY env var."""
        mock_env.setenv("SECRET_KEY", "legacy-secret-key")

        import app.config as config_module

        reload(config_module)

        assert config_module.Config.SECRET_KEY == "legacy-secret-key"

    def test_secret_key_default_when_missing(self, mock_env):
        """SECRET_KEY uses insecure default when env vars missing."""
        import app.config as config_module

        reload(config_module)

        assert config_module.Config.SECRET_KEY == "dev-key-change-in-production"

    def test_secret_not_read_from_ini(self, temp_config_dir, reload_config, mock_env):
        """SECRET_KEY should NOT be read from INI files."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[security]\nsecret_key = ini-secret-key\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        # Reload the module to pick up new config
        reload(config_module)

        # Should NOT use INI value
        assert config_module.Config.SECRET_KEY != "ini-secret-key"


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_validate_config_returns_dict(self, temp_config_dir, reload_config):
        """validate_config should return a dictionary."""
        config_module = reload_config(
            system_path=temp_config_dir["system_config"],
            user_path=temp_config_dir["user_config"],
        )

        result = config_module.validate_config()

        assert isinstance(result, dict)
        assert "camera_device" in result
        assert "alert_threshold" in result
        assert "dashboard_port" in result

    def test_validate_camera_device_range(self, temp_config_dir, reload_config, caplog):
        """Camera device out of range should log error and use fallback."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\ndevice = 99\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["camera_device"] == 0
        assert "out of range" in caplog.text

    def test_validate_camera_device_warning_when_not_found(
        self, temp_config_dir, reload_config, caplog
    ):
        """Camera device warning when /dev/videoX doesn't exist."""
        # Use device 9 which is unlikely to exist
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\ndevice = 9\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        # The warning about camera not found should be logged
        assert result["camera_device"] == 9
        assert "not found at" in caplog.text

    def test_validate_resolution_warning_for_unknown(
        self, temp_config_dir, reload_config, caplog
    ):
        """Unknown resolution should log warning."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\nresolution = 4k\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["camera_resolution"] == "4k"  # Still uses the value
        assert "Unknown resolution" in caplog.text

    def test_validate_fps_target_warning_out_of_range(
        self, temp_config_dir, reload_config, caplog
    ):
        """FPS target outside range should log warning."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[camera]\nfps_target = 120\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["camera_fps_target"] == 120  # Still uses the value
        assert (
            "FPS target" in caplog.text and "outside recommended range" in caplog.text
        )

    def test_validate_update_interval_warning_out_of_range(
        self, temp_config_dir, reload_config, caplog
    ):
        """Update interval outside range should log warning."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[dashboard]\nupdate_interval_seconds = 30\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["dashboard_update_interval"] == 30  # Still uses the value
        assert (
            "Update interval" in caplog.text
            and "outside recommended range" in caplog.text
        )

    def test_validate_port_range(self, temp_config_dir, reload_config, caplog):
        """Port out of range should log error and use fallback."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[dashboard]\nport = 80\n")  # Below 1024

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["dashboard_port"] == 5000
        assert "Port" in caplog.text and "out of range" in caplog.text

    def test_validate_threshold_range(self, temp_config_dir, reload_config, caplog):
        """Threshold out of range should log error and use fallback."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[alerts]\nposture_threshold_minutes = 100\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["alert_threshold"] == 600  # 10 minutes in seconds
        assert "out of range" in caplog.text

    def test_validate_alert_cooldown_range(self, temp_config_dir, reload_config, caplog):
        """Alert cooldown out of range should log error and use fallback."""
        user_ini = temp_config_dir["user_config"]
        user_ini.write_text("[alerts]\nalert_cooldown_minutes = 50\n")

        config_module = reload_config(
            system_path=temp_config_dir["system_config"], user_path=user_ini
        )

        result = config_module.validate_config()

        assert result["alert_cooldown"] == 300  # 5 minutes in seconds (fallback)
        assert "Alert cooldown" in caplog.text
        assert "out of range" in caplog.text


class TestTestingConfig:
    """Tests for TestingConfig isolation."""

    def test_testing_config_ignores_ini(self):
        """TestingConfig should use hardcoded values, not INI."""
        from app.config import TestingConfig

        # These should be hardcoded test values
        assert TestingConfig.CAMERA_DEVICE == 0
        assert TestingConfig.ALERT_THRESHOLD == 600
        assert TestingConfig.DASHBOARD_PORT == 5000
        assert TestingConfig.SECRET_KEY == "test-secret-key"

    def test_testing_config_has_testing_flag(self):
        """TestingConfig should have TESTING=True."""
        from app.config import TestingConfig

        assert TestingConfig.TESTING is True

    def test_testing_config_uses_memory_database(self):
        """TestingConfig should use in-memory database."""
        from app.config import TestingConfig

        assert TestingConfig.DATABASE_PATH == ":memory:"


class TestConfigClasses:
    """Tests for Config class attributes."""

    def test_base_config_has_required_attributes(self):
        """Base Config should have all required attributes."""
        from app.config import Config

        # From Story 1.1
        assert hasattr(Config, "HOST")
        assert hasattr(Config, "PORT")
        assert hasattr(Config, "DATABASE_PATH")
        assert hasattr(Config, "SECRET_KEY")

        # From Story 1.3
        assert hasattr(Config, "CAMERA_DEVICE")
        assert hasattr(Config, "CAMERA_RESOLUTION")
        assert hasattr(Config, "CAMERA_FPS_TARGET")
        assert hasattr(Config, "ALERT_THRESHOLD")
        assert hasattr(Config, "NOTIFICATION_ENABLED")
        assert hasattr(Config, "DASHBOARD_PORT")
        assert hasattr(Config, "DASHBOARD_UPDATE_INTERVAL")

    def test_development_config_inherits(self):
        """DevelopmentConfig should inherit from Config."""
        from app.config import Config, DevelopmentConfig

        assert issubclass(DevelopmentConfig, Config)
        assert DevelopmentConfig.DEBUG is True

    def test_production_config_inherits(self):
        """ProductionConfig should inherit from Config."""
        from app.config import Config, ProductionConfig

        assert issubclass(ProductionConfig, Config)
        assert ProductionConfig.DEBUG is False

    def test_systemd_config_inherits(self):
        """SystemdConfig should inherit from ProductionConfig."""
        from app.config import ProductionConfig, SystemdConfig

        assert issubclass(SystemdConfig, ProductionConfig)
        assert SystemdConfig.LOG_LEVEL == "WARNING"

    def test_legacy_alias_preserved(self):
        """POSTURE_ALERT_THRESHOLD should alias ALERT_THRESHOLD."""
        from app.config import Config

        assert Config.POSTURE_ALERT_THRESHOLD == Config.ALERT_THRESHOLD


class TestProductionConfigValidation:
    """Tests for ProductionConfig security validation."""

    def test_production_config_raises_without_secret_key(self, mock_env):
        """ProductionConfig should raise error when SECRET_KEY not set."""
        from app.config import ProductionConfig

        with pytest.raises(ValueError, match="SECURITY ERROR"):
            ProductionConfig()

    def test_production_config_succeeds_with_secret_key(self, mock_env):
        """ProductionConfig should succeed when SECRET_KEY is set."""
        mock_env.setenv("DESKPULSE_SECRET_KEY", "real-production-key")

        import app.config as config_module
        from importlib import reload

        reload(config_module)

        # Should not raise
        config = config_module.ProductionConfig()
        assert config is not None


class TestFlaskAppIntegration:
    """Tests for Flask app integration with config."""

    def test_flask_app_starts_with_no_config(self, mock_env):
        """Flask app should start with fallback values when no INI files exist."""
        mock_env.setenv("DESKPULSE_SECRET_KEY", "test-key")

        from app import create_app

        app = create_app("testing")

        assert app is not None
        assert app.config["CAMERA_DEVICE"] == 0
        assert app.config["ALERT_THRESHOLD"] == 600
        assert app.config["DASHBOARD_PORT"] == 5000

    def test_flask_app_uses_testing_config(self):
        """Flask app with testing config should use TestingConfig values."""
        from app import create_app

        app = create_app("testing")

        assert app.config["TESTING"] is True
        assert app.config["DATABASE_PATH"] == ":memory:"
        assert app.config["SECRET_KEY"] == "test-secret-key"

    def test_flask_app_with_development_config(self, mock_env):
        """Flask app with development config should have DEBUG enabled."""
        mock_env.setenv("DESKPULSE_SECRET_KEY", "test-key")

        from app import create_app

        app = create_app("development")

        assert app.config["DEBUG"] is True
