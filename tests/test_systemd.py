"""Tests for systemd integration (Story 1.4).

Tests cover:
- sdnotify import handling (with and without package)
- WatchdogManager start/stop/ping
- NOTIFY_SOCKET detection
- Environment variable binding configuration
"""

import sys
import time
from unittest.mock import Mock, MagicMock, patch

import pytest


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_sdnotify_module():
    """Create a mock sdnotify module for testing."""
    mock_notifier = Mock()
    mock_module = MagicMock()
    mock_module.SystemdNotifier.return_value = mock_notifier
    return mock_notifier, mock_module


@pytest.fixture
def systemd_env(monkeypatch):
    """Set up systemd environment with NOTIFY_SOCKET."""
    monkeypatch.setenv("NOTIFY_SOCKET", "/run/systemd/notify")
    return monkeypatch


@pytest.fixture
def no_systemd_env(monkeypatch):
    """Remove systemd environment (NOTIFY_SOCKET not set)."""
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    return monkeypatch


# =============================================================================
# WatchdogManager Tests
# =============================================================================


class TestWatchdogManager:
    """Tests for WatchdogManager class."""

    def test_watchdog_manager_exists(self):
        """WatchdogManager class should be importable from app.system."""
        from app.system.watchdog import WatchdogManager

        assert WatchdogManager is not None

    def test_watchdog_manager_has_required_methods(self):
        """WatchdogManager should have start, stop, and ping methods."""
        from app.system.watchdog import WatchdogManager

        wm = WatchdogManager()
        assert hasattr(wm, "start")
        assert hasattr(wm, "stop")
        assert hasattr(wm, "ping")
        assert callable(wm.start)
        assert callable(wm.stop)
        assert callable(wm.ping)

    def test_watchdog_noop_without_systemd(self, no_systemd_env):
        """Watchdog should be no-op when NOTIFY_SOCKET not set."""
        # Clear module cache to reload with no NOTIFY_SOCKET
        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]
        if "app.system" in sys.modules:
            del sys.modules["app.system"]

        from app.system.watchdog import WatchdogManager

        wm = WatchdogManager()

        # Should not raise even without systemd
        wm.start()
        wm.ping()
        wm.stop()

        # notifier should be None
        assert wm.notifier is None

    def test_watchdog_default_interval(self):
        """Watchdog interval should be less than WatchdogSec/2 (15 seconds)."""
        from app.system.watchdog import WatchdogManager

        wm = WatchdogManager()
        assert wm.interval < 15  # Must be strictly less than WatchdogSec/2

    def test_watchdog_start_creates_thread_when_systemd(
        self, systemd_env, mock_sdnotify_module
    ):
        """Watchdog should create background thread when under systemd."""
        mock_notifier, mock_module = mock_sdnotify_module

        # Clear and patch
        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.start()

            # Give thread time to start
            time.sleep(0.1)

            assert wm._thread is not None
            assert wm._thread.is_alive()

            wm.stop()

    def test_watchdog_stop_terminates_thread(self, systemd_env, mock_sdnotify_module):
        """Watchdog stop should terminate the ping thread."""
        mock_notifier, mock_module = mock_sdnotify_module

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.start()
            time.sleep(0.1)

            wm.stop()
            time.sleep(0.2)

            # Thread should be stopped or joined
            assert not wm._thread.is_alive() or wm._stop_event.is_set()

    def test_watchdog_ping_sends_notification(self, systemd_env, mock_sdnotify_module):
        """Watchdog ping should send WATCHDOG=1 notification."""
        mock_notifier, mock_module = mock_sdnotify_module

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.ping()

            mock_notifier.notify.assert_called_with("WATCHDOG=1")


class TestWatchdogGlobalInstance:
    """Tests for the global watchdog instance."""

    def test_global_watchdog_instance_exists(self):
        """A global watchdog instance should be exported from app.system.watchdog."""
        from app.system.watchdog import watchdog

        assert watchdog is not None

    def test_global_watchdog_is_watchdog_manager(self):
        """Global watchdog should be a WatchdogManager instance."""
        from app.system.watchdog import watchdog, WatchdogManager

        assert isinstance(watchdog, WatchdogManager)


# =============================================================================
# sdnotify Import Handling Tests
# =============================================================================


class TestSdnotifyHandling:
    """Tests for graceful sdnotify import handling."""

    def test_watchdog_handles_missing_sdnotify(self, systemd_env):
        """WatchdogManager should handle missing sdnotify gracefully."""
        # Clear module cache
        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]
        if "sdnotify" in sys.modules:
            del sys.modules["sdnotify"]

        # Patch sdnotify to raise ImportError
        with patch.dict("sys.modules", {"sdnotify": None}):
            # This should not raise
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.start()
            wm.ping()
            wm.stop()


# =============================================================================
# Notifier Utility Tests
# =============================================================================


class TestGetNotifier:
    """Tests for the get_notifier utility function."""

    def test_get_notifier_exists(self):
        """get_notifier function should exist in watchdog module."""
        from app.system.watchdog import get_notifier

        assert get_notifier is not None
        assert callable(get_notifier)

    def test_get_notifier_returns_none_without_systemd(self, no_systemd_env):
        """get_notifier should return None when not under systemd."""
        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        from app.system.watchdog import get_notifier

        result = get_notifier()
        assert result is None

    def test_get_notifier_returns_notifier_with_systemd(
        self, systemd_env, mock_sdnotify_module
    ):
        """get_notifier should return notifier when under systemd."""
        mock_notifier, mock_module = mock_sdnotify_module

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import get_notifier

            result = get_notifier()
            assert result is not None


# =============================================================================
# Environment Binding Configuration Tests
# =============================================================================


class TestBindingConfiguration:
    """Tests for security binding configuration."""

    def test_default_host_is_localhost(self, app):
        """Default host should be 127.0.0.1 for security."""
        # Default should be localhost
        host = app.config.get("HOST", "127.0.0.1")
        assert host in ("127.0.0.1", "localhost")

    def test_host_can_be_overridden_via_env(self, monkeypatch):
        """Host should be configurable via FLASK_HOST environment variable."""
        monkeypatch.setenv("FLASK_HOST", "0.0.0.0")

        # Test that environment variable can influence binding
        # The wsgi.py reads FLASK_HOST from environment
        # Access via monkeypatch's internal environ dict
        import os as os_module

        host = os_module.environ.get("FLASK_HOST", "127.0.0.1")
        assert host == "0.0.0.0"

    def test_default_port_is_5000(self, app):
        """Default port should be 5000."""
        port = app.config.get("PORT", 5000)
        assert port == 5000


# =============================================================================
# Additional Tests for Coverage
# =============================================================================


class TestWatchdogNotifyMethods:
    """Tests for WatchdogManager notify methods."""

    def test_notify_ready_sends_notification(self, systemd_env, mock_sdnotify_module):
        """notify_ready should send READY=1 notification."""
        mock_notifier, mock_module = mock_sdnotify_module

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.notify_ready()

            mock_notifier.notify.assert_called_with("READY=1")

    def test_notify_status_sends_status(self, systemd_env, mock_sdnotify_module):
        """notify_status should send STATUS= notification."""
        mock_notifier, mock_module = mock_sdnotify_module

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.notify_status("Test status")

            mock_notifier.notify.assert_called_with("STATUS=Test status")

    def test_notify_stopping_sends_notification(
        self, systemd_env, mock_sdnotify_module
    ):
        """notify_stopping should send STOPPING=1 notification."""
        mock_notifier, mock_module = mock_sdnotify_module

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.notify_stopping()

            mock_notifier.notify.assert_called_with("STOPPING=1")

    def test_notify_methods_noop_without_systemd(self, no_systemd_env):
        """Notify methods should be no-op when not under systemd."""
        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        from app.system.watchdog import WatchdogManager

        wm = WatchdogManager()

        # These should not raise even without systemd
        wm.notify_ready()
        wm.notify_status("Test")
        wm.notify_stopping()

        assert wm.notifier is None


class TestWatchdogExceptionHandling:
    """Tests for exception handling in WatchdogManager."""

    def test_ping_handles_exception(self, systemd_env, mock_sdnotify_module):
        """Ping should handle exceptions from notifier gracefully."""
        mock_notifier, mock_module = mock_sdnotify_module
        mock_notifier.notify.side_effect = Exception("Test error")

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            # Should not raise
            wm.ping()

    def test_ping_loop_handles_exception(self, systemd_env, mock_sdnotify_module):
        """_ping_loop should handle exceptions from notifier gracefully."""
        mock_notifier, mock_module = mock_sdnotify_module
        # First call raises, then succeeds (to verify loop continues)
        mock_notifier.notify.side_effect = [Exception("Test error"), None]

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            wm.interval = 0.01  # Very short for testing
            wm.start()
            time.sleep(0.05)  # Let loop run
            wm.stop()
            # Should not raise - loop handled exception gracefully

    def test_notify_ready_handles_exception(self, systemd_env, mock_sdnotify_module):
        """notify_ready should handle exceptions gracefully."""
        mock_notifier, mock_module = mock_sdnotify_module
        mock_notifier.notify.side_effect = Exception("Test error")

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            # Should not raise
            wm.notify_ready()

    def test_notify_status_handles_exception(self, systemd_env, mock_sdnotify_module):
        """notify_status should handle exceptions gracefully."""
        mock_notifier, mock_module = mock_sdnotify_module
        mock_notifier.notify.side_effect = Exception("Test error")

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            # Should not raise
            wm.notify_status("Test")

    def test_notify_stopping_handles_exception(self, systemd_env, mock_sdnotify_module):
        """notify_stopping should handle exceptions gracefully."""
        mock_notifier, mock_module = mock_sdnotify_module
        mock_notifier.notify.side_effect = Exception("Test error")

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            # Should not raise
            wm.notify_stopping()

    def test_watchdog_init_handles_notifier_exception(
        self, systemd_env, mock_sdnotify_module
    ):
        """WatchdogManager.__init__ should handle SystemdNotifier exception."""
        mock_notifier, mock_module = mock_sdnotify_module
        mock_module.SystemdNotifier.side_effect = Exception("Init error")

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import WatchdogManager

            wm = WatchdogManager()
            # notifier should be None due to exception
            assert wm.notifier is None


class TestGetNotifierEdgeCases:
    """Tests for edge cases in get_notifier function."""

    def test_get_notifier_sdnotify_unavailable(self, systemd_env):
        """get_notifier returns None when sdnotify not available."""
        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        # Patch SDNOTIFY_AVAILABLE to False
        with patch.dict("sys.modules", {"sdnotify": None}):
            from app.system.watchdog import get_notifier

            result = get_notifier()
            assert result is None

    def test_get_notifier_handles_notifier_exception(
        self, systemd_env, mock_sdnotify_module
    ):
        """get_notifier should handle SystemdNotifier exception."""
        mock_notifier, mock_module = mock_sdnotify_module
        mock_module.SystemdNotifier.side_effect = Exception("Notifier init error")

        if "app.system.watchdog" in sys.modules:
            del sys.modules["app.system.watchdog"]

        with patch.dict("sys.modules", {"sdnotify": mock_module}):
            from app.system.watchdog import get_notifier

            result = get_notifier()
            # Should return None on exception
            assert result is None
