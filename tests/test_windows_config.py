"""Tests for Windows Desktop Client Configuration Management."""
import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Note: These tests can run on any platform
# Windows-specific behavior is mocked where needed
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.windows_client.config import (
    get_config_path,
    validate_backend_url,
    load_config,
    save_config,
    watch_config_changes,
    DEFAULT_CONFIG
)


class TestValidateBackendUrl:
    """Test backend URL validation (security requirement NFR-S1)."""

    def test_valid_localhost(self):
        """Test localhost URLs are accepted."""
        assert validate_backend_url("http://localhost:5000") == "http://localhost:5000"
        assert validate_backend_url("https://localhost:5000") == "https://localhost:5000"

    def test_valid_127_x_x_x(self):
        """Test 127.x.x.x URLs are accepted."""
        assert validate_backend_url("http://127.0.0.1:5000") == "http://127.0.0.1:5000"
        assert validate_backend_url("http://127.1.2.3:5000") == "http://127.1.2.3:5000"

    def test_valid_192_168_x_x(self):
        """Test 192.168.x.x URLs are accepted."""
        assert validate_backend_url("http://192.168.1.100:5000") == "http://192.168.1.100:5000"
        assert validate_backend_url("http://192.168.50.25:5000") == "http://192.168.50.25:5000"

    def test_valid_10_x_x_x(self):
        """Test 10.x.x.x URLs are accepted."""
        assert validate_backend_url("http://10.0.0.1:5000") == "http://10.0.0.1:5000"
        assert validate_backend_url("http://10.50.100.200:5000") == "http://10.50.100.200:5000"

    def test_valid_172_16_31_x_x(self):
        """Test 172.16-31.x.x URLs are accepted."""
        assert validate_backend_url("http://172.16.0.1:5000") == "http://172.16.0.1:5000"
        assert validate_backend_url("http://172.31.255.255:5000") == "http://172.31.255.255:5000"

    def test_valid_mdns(self):
        """Test mDNS (*.local) URLs are accepted."""
        assert validate_backend_url("http://raspberrypi.local:5000") == "http://raspberrypi.local:5000"
        assert validate_backend_url("http://myserver.local:5000") == "http://myserver.local:5000"

    def test_invalid_protocol(self):
        """Test non-HTTP(S) protocols are rejected."""
        with pytest.raises(ValueError, match="Invalid protocol"):
            validate_backend_url("ftp://localhost:5000")
        with pytest.raises(ValueError, match="Invalid protocol"):
            validate_backend_url("ws://localhost:5000")

    def test_missing_hostname(self):
        """Test URLs without hostname are rejected."""
        with pytest.raises(ValueError, match="Missing hostname"):
            validate_backend_url("http://")

    def test_external_url_rejected(self):
        """Test external URLs are rejected (privacy requirement)."""
        with pytest.raises(ValueError, match="External URLs not allowed"):
            validate_backend_url("http://example.com:5000")
        with pytest.raises(ValueError, match="External URLs not allowed"):
            validate_backend_url("https://8.8.8.8:5000")
        with pytest.raises(ValueError, match="External URLs not allowed"):
            validate_backend_url("http://172.15.0.1:5000")  # Outside 172.16-31 range


class TestGetConfigPath:
    """Test config path resolution with fallback."""

    @patch.dict(os.environ, {'APPDATA': '/mock/appdata', 'TEMP': '/mock/temp'})
    @patch('app.windows_client.config.Path.mkdir')
    @patch('app.windows_client.config.Path.touch')
    @patch('app.windows_client.config.Path.unlink')
    def test_appdata_path(self, mock_unlink, mock_touch, mock_mkdir):
        """Test config path uses APPDATA when writable."""
        config_path = get_config_path()
        assert 'appdata' in str(config_path).lower()
        assert 'DeskPulse' in str(config_path)
        assert config_path.name == 'config.json'

    def test_fallback_to_temp(self):
        """Test fallback to TEMP when APPDATA not writable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a read-only directory to simulate unwritable APPDATA
            appdata_dir = Path(tmpdir) / 'appdata'
            appdata_dir.mkdir()

            # Make it read-only by testing permission via touch failure
            with patch.dict(os.environ, {'APPDATA': str(appdata_dir), 'TEMP': tmpdir}):
                with patch('app.windows_client.config.Path.touch', side_effect=PermissionError("No write access")):
                    config_path = get_config_path()
                    # Should fall back to TEMP directory
                    assert tmpdir in str(config_path)
                    assert 'DeskPulse' in str(config_path)

    @patch.dict(os.environ, {}, clear=True)
    def test_no_appdata_env(self):
        """Test behavior when APPDATA env var doesn't exist."""
        # Set TEMP to a real temp directory for this test
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {'TEMP': tmpdir}):
                config_path = get_config_path()
                assert 'DeskPulse' in str(config_path)
                assert config_path.name == 'config.json'


class TestLoadConfig:
    """Test config loading with validation and error handling."""

    def test_load_missing_config_creates_default(self):
        """Test loading non-existent config creates default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                config = load_config()

                # Should return defaults
                assert config['backend_url'] == DEFAULT_CONFIG['backend_url']
                assert config['version'] == DEFAULT_CONFIG['version']

                # Should create file
                assert config_file.exists()

    def test_load_valid_config(self):
        """Test loading valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'
            test_config = {
                "backend_url": "http://192.168.1.100:5000",
                "version": "1.0.0"
            }

            # Create config file
            with open(config_file, 'w') as f:
                json.dump(test_config, f)

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                config = load_config()

                assert config['backend_url'] == "http://192.168.1.100:5000"
                assert config['version'] == "1.0.0"

    def test_load_corrupted_json_recreates(self):
        """Test corrupted JSON is detected and recreated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'

            # Create corrupted JSON
            with open(config_file, 'w') as f:
                f.write("{invalid json content}")

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                config = load_config()

                # Should return defaults
                assert config['backend_url'] == DEFAULT_CONFIG['backend_url']

                # Should recreate valid file
                with open(config_file, 'r') as f:
                    recreated = json.load(f)
                    assert recreated['backend_url'] == DEFAULT_CONFIG['backend_url']

    def test_load_invalid_backend_url_raises(self):
        """Test invalid backend URL raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'
            test_config = {
                "backend_url": "http://example.com:5000",  # External URL
                "version": "1.0.0"
            }

            with open(config_file, 'w') as f:
                json.dump(test_config, f)

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                with pytest.raises(ValueError, match="External URLs not allowed"):
                    load_config()

    def test_load_missing_backend_url_uses_default(self):
        """Test missing backend_url uses default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'
            test_config = {"version": "1.0.0"}  # No backend_url

            with open(config_file, 'w') as f:
                json.dump(test_config, f)

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                config = load_config()

                assert config['backend_url'] == DEFAULT_CONFIG['backend_url']


class TestSaveConfig:
    """Test config saving with validation."""

    def test_save_valid_config(self):
        """Test saving valid config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'
            test_config = {
                "backend_url": "http://192.168.1.100:5000",
                "version": "1.0.0"
            }

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                save_config(test_config)

                # Verify file created
                assert config_file.exists()

                # Verify content
                with open(config_file, 'r') as f:
                    saved = json.load(f)
                    assert saved['backend_url'] == "http://192.168.1.100:5000"
                    assert saved['version'] == "1.0.0"

    def test_save_invalid_backend_url_raises(self):
        """Test saving config with invalid backend_url raises."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'
            test_config = {
                "backend_url": "http://example.com:5000",  # External URL
                "version": "1.0.0"
            }

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                with pytest.raises(ValueError, match="External URLs not allowed"):
                    save_config(test_config)


class TestWatchConfigChanges:
    """Test config change detection."""

    def test_no_changes_detected(self):
        """Test no changes when config unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                # Load config (sets mtime)
                load_config()

                # Check immediately (no changes)
                assert watch_config_changes() is False

    def test_changes_detected(self):
        """Test changes detected when config modified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config.json'

            with patch('app.windows_client.config.get_config_path', return_value=config_file):
                # Load config (sets mtime)
                config = load_config()

                # Modify config file
                import time
                time.sleep(0.01)  # Ensure mtime changes
                config['backend_url'] = "http://192.168.1.200:5000"
                with open(config_file, 'w') as f:
                    json.dump(config, f)

                # Check for changes
                assert watch_config_changes() is True

    def test_watch_before_load(self):
        """Test watch returns False if never loaded."""
        import app.windows_client.config as config_module
        # Reset module state
        config_module._last_config_mtime = None

        assert watch_config_changes() is False
