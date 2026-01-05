"""DeskPulse Windows Desktop Client - System Tray Manager."""
import logging
import webbrowser
import platform
from typing import Dict, Optional, Any, TYPE_CHECKING

logger = logging.getLogger('deskpulse.windows.tray')

# Conditional imports for Windows-only dependencies
try:
    import pystray
    from PIL import Image, ImageDraw
    WINDOWS_AVAILABLE = True
except ImportError:
    # Create stub classes for test patching (C1 fix)
    pystray = None  # type: ignore
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    WINDOWS_AVAILABLE = False
    logger.warning("pystray/Pillow not available - Windows features disabled")

# Type checking imports (not executed at runtime)
if TYPE_CHECKING:
    from PIL import Image as ImageType
    import pystray as pystray_typing

# Icon state color mappings (centralized for consistency)
STATE_COLORS = {
    'connected': (0, 200, 0, 255),    # Green: Connected, monitoring active
    'paused': (128, 128, 128, 255),   # Gray: Connected, monitoring paused
    'disconnected': (200, 0, 0, 255)  # Red: Disconnected from backend
}


class TrayManager:
    """
    System tray manager for Windows desktop client.

    Manages system tray icon with 3 states (green/gray/red),
    context menu, and tooltip with live stats.
    """

    def __init__(self, backend_url: str, socketio_client: Any):
        """
        Initialize TrayManager.

        Args:
            backend_url: Backend URL for opening dashboard
            socketio_client: Reference to SocketIOClient for emitting events
        """
        if not WINDOWS_AVAILABLE:
            raise ImportError("pystray and Pillow are required for TrayManager")

        self.backend_url = backend_url
        self.socketio_client = socketio_client
        self.monitoring_active = True  # Synced from backend on connect
        self._emit_in_progress = False  # Prevent duplicate pause/resume clicks
        self._last_refresh_time = 0.0  # Rate limiting for manual refresh (M2 fix)

        # Pre-cache icon images (optimization)
        self.icon_cache: Dict[str, Any] = {}  # Image.Image when PIL available
        self.create_icon_images()

        # Tray icon instance (created in run())
        self.icon: Optional[pystray.Icon] = None

        logger.info("TrayManager initialized")

    def create_icon_images(self):
        """
        Pre-generate and cache all icon states.

        Creates 3 icons:
        - connected: Green (monitoring active)
        - paused: Gray (monitoring paused)
        - disconnected: Red (backend disconnected)

        Falls back to solid color if Pillow fails.
        """
        try:
            self.icon_cache = {
                'connected': self._generate_icon('connected'),
                'paused': self._generate_icon('paused'),
                'disconnected': self._generate_icon('disconnected')
            }
            logger.info("Icon images cached successfully")
        except Exception as e:
            logger.error(f"Error creating icon images: {e}")
            # Fall back to solid color icons
            self.icon_cache = {
                'connected': self._generate_fallback_icon('connected'),
                'paused': self._generate_fallback_icon('paused'),
                'disconnected': self._generate_fallback_icon('disconnected')
            }

    def _generate_icon(self, state: str) -> 'Image.Image':
        """
        Generate posture icon (head + spine graphic).

        Args:
            state: Icon state (connected/paused/disconnected)

        Returns:
            PIL Image (64x64 pixels)
        """
        # Create 64x64 image (Windows standard)
        img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Get fill color from centralized mapping
        fill_color = STATE_COLORS.get(state, STATE_COLORS['connected'])

        # Draw simple posture representation (head + spine)
        # Head (circle at top)
        draw.ellipse([20, 8, 44, 32], fill=fill_color)

        # Spine (vertical line)
        draw.rectangle([30, 32, 34, 56], fill=fill_color)

        return img

    def _generate_fallback_icon(self, state: str) -> 'Image.Image':
        """
        Generate solid color icon as fallback.

        Args:
            state: Icon state (connected/paused/disconnected)

        Returns:
            PIL Image (64x64 pixels)
        """
        # Use RGB tuple from STATE_COLORS (not string)
        fill_color = STATE_COLORS.get(state, STATE_COLORS['connected'])
        # Convert RGBA to RGB for fallback
        rgb_color = fill_color[:3]
        img = Image.new('RGB', (64, 64), color=rgb_color)
        return img

    def get_icon_image(self, state: str) -> 'Image.Image':
        """
        Get cached icon for state.

        Args:
            state: Icon state ('connected', 'paused', 'disconnected')

        Returns:
            PIL Image
        """
        return self.icon_cache.get(state, self.icon_cache['connected'])

    def update_icon_state(self, state: str):
        """
        Update tray icon to reflect state.

        Args:
            state: Icon state ('connected', 'paused', 'disconnected')
        """
        if self.icon:
            self.icon.icon = self.get_icon_image(state)
            logger.info(f"Icon updated to state: {state}")

    def update_tooltip(self, stats: Optional[Dict[str, Any]] = None):
        """
        Update tooltip with live stats or disconnected message.

        Args:
            stats: Stats dict from /api/stats/today, or None if disconnected
        """
        if stats:
            # Format tooltip with stats
            score = stats.get('posture_score', 0)
            duration_seconds = stats.get('good_duration_seconds', 0)

            # Convert seconds to hours and minutes
            hours = duration_seconds // 3600
            minutes = (duration_seconds % 3600) // 60

            tooltip = f"DeskPulse - Today: {score:.0f}% good posture, {hours}h {minutes}m tracked"
        else:
            tooltip = "DeskPulse - Disconnected"

        if self.icon:
            self.icon.title = tooltip
            logger.info(f"Tooltip updated: {tooltip}")

    def on_clicked(self, icon, item):
        """
        Handle left-click or double-click on icon.

        Opens dashboard in default browser.
        """
        logger.info("Opening dashboard in browser")
        try:
            webbrowser.open(self.backend_url)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            # Show MessageBox if browser fails to open
            try:
                import ctypes
                MB_OK = 0x0
                MB_SYSTEMMODAL = 0x1000
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"Failed to open browser.\n\n"
                    f"Please visit manually:\n{self.backend_url}\n\n"
                    f"Error: {e}",
                    "DeskPulse",
                    MB_OK | MB_SYSTEMMODAL
                )
            except Exception:
                pass  # MessageBox failed, already logged error

    def on_pause(self, icon, item):
        """
        Handle "Pause Monitoring" menu selection.

        Emits pause_monitoring to backend.
        Icon update handled by monitoring_status event from backend.
        Prevents duplicate clicks with _emit_in_progress flag.
        """
        if self._emit_in_progress:
            logger.warning("Emit already in progress, ignoring pause request")
            return

        logger.info("Pause monitoring requested")
        self._emit_in_progress = True
        self.socketio_client.emit_pause()

    def on_resume(self, icon, item):
        """
        Handle "Resume Monitoring" menu selection.

        Emits resume_monitoring to backend.
        Icon update handled by monitoring_status event from backend.
        Prevents duplicate clicks with _emit_in_progress flag.
        """
        if self._emit_in_progress:
            logger.warning("Emit already in progress, ignoring resume request")
            return

        logger.info("Resume monitoring requested")
        self._emit_in_progress = True
        self.socketio_client.emit_resume()

    def on_view_today_stats(self, icon, item):
        """
        Handle "View Stats → Today's Stats" menu selection.

        Fetches real stats from /api/stats/today and displays in MessageBox.
        Enterprise-grade error handling with user-friendly messages.
        """
        logger.info("View today's stats requested")

        try:
            from app.windows_client.api_client import APIClient
            import ctypes

            # Create API client and fetch stats
            client = APIClient(self.backend_url)
            stats = client.get_today_stats()

            if stats:
                # Format stats message
                good_seconds = stats.get('good_duration_seconds', 0)
                bad_seconds = stats.get('bad_duration_seconds', 0)
                score = stats.get('posture_score', 0)
                total_events = stats.get('total_events', 0)

                # Convert seconds to hours and minutes (M1 fix: AC3 format)
                good_hours = good_seconds // 3600
                good_min = (good_seconds % 3600) // 60
                total_good_min = good_seconds // 60
                bad_min = bad_seconds // 60

                # AC3: Show both formats when >60 min
                if total_good_min > 60:
                    good_time = f"{total_good_min} minutes ({good_hours}h {good_min}m)"
                else:
                    good_time = f"{total_good_min} minutes"

                message = (
                    f"Today's Posture Statistics\n\n"
                    f"Good Posture: {good_time}\n"
                    f"Bad Posture: {bad_min} minutes\n"
                    f"Posture Score: {score:.0f}%\n"
                    f"Total Events: {total_events}"
                )
            else:
                # API call failed
                message = (
                    f"Failed to retrieve stats.\n"
                    f"Check connection to Raspberry Pi.\n\n"
                    f"Backend: {self.backend_url}"
                )

            # Show MessageBox (MB_OK | MB_SYSTEMMODAL for proper focus)
            MB_OK = 0x0
            MB_SYSTEMMODAL = 0x1000
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                "DeskPulse Stats",
                MB_OK | MB_SYSTEMMODAL  # System modal - always on top, gets focus
            )

            logger.info("Today's stats displayed")

        except Exception as e:
            logger.exception(f"Error displaying today's stats: {e}")

    def on_view_history(self, icon, item):
        """
        Handle "View Stats → 7-Day History" menu selection.

        Opens dashboard in browser (dashboard has 7-day table).
        """
        logger.info("Opening 7-day history in browser")
        try:
            webbrowser.open(self.backend_url)
        except Exception as e:
            logger.error(f"Failed to open browser for history: {e}")

    def on_refresh_stats(self, icon, item):
        """
        Handle "View Stats → Refresh" menu selection.

        Forces immediate tooltip update from API (bypasses 60s timer).

        M2 fix: Rate limiting - 3 second cooldown to prevent API spam.
        """
        import time

        # M2 fix: Rate limiting (3 second cooldown)
        now = time.time()
        if now - self._last_refresh_time < 3.0:
            logger.warning("Refresh stats rate limited (3s cooldown)")
            return

        logger.info("Stats manually refreshed from API")
        self._last_refresh_time = now

        try:
            self._update_tooltip_from_api()
        except Exception as e:
            logger.error(f"Failed to refresh stats: {e}")

    def _update_tooltip_from_api(self):
        """
        Update tooltip with live stats from API.

        Called by on_refresh_stats() and periodic update timer.
        Fetches from /api/stats/today and updates tooltip.
        """
        try:
            from app.windows_client.api_client import APIClient

            client = APIClient(self.backend_url)
            stats = client.get_today_stats()

            if stats:
                self.update_tooltip(stats)
            else:
                # API call failed
                self.update_tooltip(None)

        except Exception as e:
            logger.exception(f"Error updating tooltip from API: {e}")
            self.update_tooltip(None)

    def on_settings(self, icon, item):
        """
        Handle "Settings" menu selection (Enhanced for Story 7.4).

        Shows MessageBox with backend URL, config path, and reload instructions.
        """
        logger.info("Settings menu clicked")
        try:
            import ctypes
            from app.windows_client.config import get_config_path

            config_path = get_config_path()
            message = (
                f"DeskPulse Settings\n\n"
                f"Backend URL: {self.backend_url}\n"
                f"Config File: {config_path}\n\n"
                f"To change settings, edit the config file and save.\n"
                f"DeskPulse will automatically reload within 10 seconds.\n\n"
                f"Note: Changing backend URL requires valid local network address."
            )

            MB_OK = 0x0
            MB_SYSTEMMODAL = 0x1000
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                "DeskPulse Settings",
                MB_OK | MB_SYSTEMMODAL  # System modal - always on top, gets focus
            )
        except Exception as e:
            logger.exception(f"Error showing settings: {e}")

    def on_about(self, icon, item):
        """
        Handle "About" menu selection (Enhanced for Story 7.4).

        Shows MessageBox with version, platform info, and project link.
        """
        logger.info("About menu clicked")
        try:
            import ctypes
            from app.windows_client import __version__

            # Get platform information
            system = platform.system()
            release = platform.release()
            version = platform.version()
            python_ver = platform.python_version()

            message = (
                f"DeskPulse Windows Client\n\n"
                f"Version: {__version__}\n"
                f"Platform: {system} {release} ({version})\n"
                f"Python: {python_ver}\n\n"
                f"Privacy-first posture monitoring\n"
                f"Runs on Raspberry Pi, connects locally\n\n"
                f"GitHub: https://github.com/yourusername/deskpulse\n"
                f"License: MIT\n\n"
                f"🤖 Generated with Claude Code"
            )

            MB_OK = 0x0
            MB_SYSTEMMODAL = 0x1000
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                "About DeskPulse",
                MB_OK | MB_SYSTEMMODAL
            )
        except Exception as e:
            logger.exception(f"Error showing about: {e}")

    def on_exit(self, icon, item):
        """
        Handle "Exit" menu selection.

        Gracefully terminates application:
        - Disconnects SocketIO
        - Flushes logs
        - Stops tray icon
        """
        logger.info("Exiting DeskPulse Windows client")

        # Disconnect SocketIO
        self.socketio_client.disconnect()

        # Flush logs
        for handler in logging.root.handlers:
            handler.flush()

        # Stop icon (exits run loop)
        if icon:
            icon.stop()

    def create_menu(self) -> Any:  # pystray.Menu when pystray available
        """
        Create enhanced context menu with View Stats submenu (Story 7.4).

        Menu Structure:
        - Open Dashboard (default, bold)
        - Separator
        - Pause Monitoring (enabled when monitoring_active)
        - Resume Monitoring (enabled when not monitoring_active)
        - Separator
        - View Stats (submenu):
          - Today's Stats
          - 7-Day History
          - Refresh Stats
        - Separator
        - Settings
        - About
        - Separator
        - Exit DeskPulse

        Returns:
            pystray.Menu instance
        """
        return pystray.Menu(
            pystray.MenuItem(
                "Open Dashboard",
                self.on_clicked,
                default=True  # Bold, activated on left-click
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Pause Monitoring",
                self.on_pause,
                enabled=lambda item: self.monitoring_active and not self._emit_in_progress
            ),
            pystray.MenuItem(
                "Resume Monitoring",
                self.on_resume,
                enabled=lambda item: not self.monitoring_active and not self._emit_in_progress
            ),
            pystray.Menu.SEPARATOR,
            # View Stats submenu (Story 7.4)
            pystray.MenuItem(
                "View Stats",
                pystray.Menu(
                    pystray.MenuItem("Today's Stats", self.on_view_today_stats),
                    pystray.MenuItem("7-Day History", self.on_view_history),
                    pystray.MenuItem("Refresh Stats", self.on_refresh_stats)
                )
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self.on_settings),
            pystray.MenuItem("About", self.on_about),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit DeskPulse", self.on_exit)
        )

    def run(self):
        """
        Run system tray icon (blocking call).

        Creates pystray.Icon with green icon and initial tooltip.
        Blocks until icon.stop() is called (via Exit menu).
        """
        # Create icon with initial state (green - connected)
        self.icon = pystray.Icon(
            "DeskPulse",
            self.get_icon_image('connected'),
            "DeskPulse - Connecting...",
            self.create_menu()
        )

        logger.info("Starting system tray icon (blocking)")
        self.icon.run()
        logger.info("System tray icon stopped")
