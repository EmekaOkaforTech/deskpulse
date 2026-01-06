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
# Professional teal color scheme (enterprise-grade)
STATE_COLORS = {
    'connected': (0, 139, 139, 255),    # Teal: Connected, monitoring active (professional)
    'paused': (128, 128, 128, 255),     # Gray: Connected, monitoring paused
    'disconnected': (200, 0, 0, 255)    # Red: Disconnected from backend
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

    def _show_message_box(self, title: str, message: str):
        """
        Show Windows MessageBox that properly responds to OK/X buttons.

        Uses threading to ensure message loop works correctly from tray context.

        Args:
            title: MessageBox title
            message: MessageBox message
        """
        import threading
        import ctypes

        def show_box():
            # MB_OK | MB_TASKMODAL | MB_SETFOREGROUND
            # Using proper flags for tray application
            ctypes.windll.user32.MessageBoxW(
                None,
                message,
                title,
                0x0 | 0x2000 | 0x10000
            )

        # Run MessageBox in separate thread with proper Windows message loop
        thread = threading.Thread(target=show_box, daemon=False)
        thread.start()

    def _show_yes_no_dialog(self, title: str, message: str) -> bool:
        """
        Show Windows Yes/No dialog that properly responds to buttons.

        Uses threading to ensure message loop works correctly from tray context.

        Args:
            title: Dialog title
            message: Dialog message

        Returns:
            bool: True if user clicked Yes, False if No or closed
        """
        import threading
        import ctypes

        result_container = [None]  # Container to pass result from thread

        def show_dialog():
            MB_YESNO = 0x4
            MB_ICONWARNING = 0x30
            MB_DEFBUTTON2 = 0x100
            MB_TASKMODAL = 0x2000
            MB_SETFOREGROUND = 0x10000
            IDYES = 6

            result = ctypes.windll.user32.MessageBoxW(
                None,
                message,
                title,
                MB_YESNO | MB_ICONWARNING | MB_DEFBUTTON2 | MB_TASKMODAL | MB_SETFOREGROUND
            )
            result_container[0] = (result == IDYES)

        # Run dialog in separate thread
        thread = threading.Thread(target=show_dialog, daemon=False)
        thread.start()
        thread.join()  # Wait for user response

        return result_container[0] if result_container[0] is not None else False

    def create_icon_images(self):
        """
        Load professional icon from .ico file and create colored variants.

        Loads professional icon_professional.ico (person at desk with monitor)
        and creates colored variants for different states.

        Creates 3 icons:
        - connected: Teal (monitoring active)
        - paused: Gray (monitoring paused)
        - disconnected: Red (backend disconnected)

        Falls back to generated icon if .ico file not found.
        """
        import os

        try:
            # Try to load professional .ico file first
            icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'assets', 'windows', 'icon_professional.ico'
            )

            if os.path.exists(icon_path):
                # Load base icon and create colored variants
                base_img = Image.open(icon_path)
                # Get the 64x64 size from multi-resolution .ico
                if hasattr(base_img, 'size') and base_img.size != (64, 64):
                    base_img = base_img.resize((64, 64), Image.Resampling.LANCZOS)

                self.icon_cache = {
                    'connected': base_img.copy(),  # Uses teal from .ico
                    'paused': self._colorize_icon(base_img, (128, 128, 128, 255)),
                    'disconnected': self._colorize_icon(base_img, (200, 0, 0, 255))
                }
                logger.info(f"Professional icon loaded from {icon_path}")
            else:
                # Fallback to generated icon
                logger.warning(f"Icon file not found: {icon_path}, generating fallback")
                self.icon_cache = {
                    'connected': self._generate_icon('connected'),
                    'paused': self._generate_icon('paused'),
                    'disconnected': self._generate_icon('disconnected')
                }
        except Exception as e:
            logger.error(f"Error loading icon: {e}, using fallback")
            # Fall back to generated icons
            self.icon_cache = {
                'connected': self._generate_icon('connected'),
                'paused': self._generate_icon('paused'),
                'disconnected': self._generate_icon('disconnected')
            }

    def _colorize_icon(self, img: 'Image.Image', color: tuple) -> 'Image.Image':
        """
        Colorize icon to specific color while preserving shape.

        Args:
            img: Source image
            color: RGBA color tuple

        Returns:
            Colorized image
        """
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Create colored version
        colored = Image.new('RGBA', img.size, (0, 0, 0, 0))
        pixels = img.load()
        colored_pixels = colored.load()

        for y in range(img.size[1]):
            for x in range(img.size[0]):
                r, g, b, a = pixels[x, y]
                if a > 0:  # Only colorize non-transparent pixels
                    colored_pixels[x, y] = color

        return colored

    def _generate_icon(self, state: str) -> 'Image.Image':
        """
        Generate professional DeskPulse icon (person at desk with monitor).

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

        # Professional DeskPulse icon design
        # Represents: Person sitting at desk with monitor (posture monitoring)

        # Monitor/screen (top - represents desk workspace)
        draw.rectangle([18, 8, 46, 28], fill=fill_color, outline=fill_color)
        # Monitor stand (small base)
        draw.rectangle([30, 28, 34, 32], fill=fill_color)

        # Person sitting (below monitor)
        # Head (circle)
        draw.ellipse([26, 34, 38, 46], fill=fill_color)

        # Torso/body (sitting posture)
        draw.rounded_rectangle([24, 46, 40, 56], radius=2, fill=fill_color)

        # Desk surface (horizontal line at bottom)
        draw.rectangle([12, 58, 52, 60], fill=fill_color)

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
            # Force menu refresh to update enabled/disabled states
            self.icon.update_menu()
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
                message = (
                    f"Failed to open browser.\n\n"
                    f"Please visit manually:\n{self.backend_url}\n\n"
                    f"Error: {e}"
                )
                self._show_message_box("DeskPulse", message)
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

            # Show MessageBox using helper (proper threading for tray)
            self._show_message_box("DeskPulse Stats", message)
            logger.info("Today's stats displayed")

        except Exception as e:
            logger.exception(f"Error displaying today's stats: {e}")

    def on_view_history(self, icon, item):
        """
        Handle "View Stats → 7-Day History" menu selection.

        Fetches 7-day history from API and displays in MessageBox.
        Shows daily posture scores with durations in user-friendly format.
        """
        logger.info("Fetching 7-day history from API")
        try:
            import requests
            from datetime import datetime

            # Fetch history from backend API
            response = requests.get(
                f"{self.backend_url}/api/stats/history",
                timeout=5
            )

            if response.status_code != 200:
                self._show_message_box(
                    "7-Day History",
                    f"Failed to fetch history from backend.\n\n"
                    f"Status: {response.status_code}\n"
                    f"Please check backend connection."
                )
                return

            data = response.json()
            history = data.get('history', [])

            if not history:
                self._show_message_box(
                    "7-Day History",
                    "No posture data available yet.\n\n"
                    "Start using DeskPulse to build your history!"
                )
                return

            # Format history for professional display
            lines = []
            lines.append("╔" + "═" * 58 + "╗\n")
            lines.append("║" + " " * 12 + "7-DAY POSTURE PERFORMANCE REPORT" + " " * 14 + "║\n")
            lines.append("╠" + "═" * 58 + "╣\n")
            lines.append("║  Date       Score    Status        Good    Bad       ║\n")
            lines.append("╠" + "═" * 58 + "╣\n")

            for day in history:
                date_obj = datetime.fromisoformat(day['date'])
                day_name = date_obj.strftime('%a %m/%d')
                score = day['posture_score']

                # Convert seconds to hours (rounded to 1 decimal)
                good_hours = day['good_duration_seconds'] / 3600
                bad_hours = day['bad_duration_seconds'] / 3600

                # Format score with visual indicator
                if score >= 80:
                    status = "Excellent"
                    icon = "✓"
                elif score >= 60:
                    status = "Good     "
                    icon = "○"
                else:
                    status = "Needs Work"
                    icon = "△"

                # Professional aligned format
                lines.append(
                    f"║  {day_name:8}  {score:5.0f}%   {icon} {status:10}  "
                    f"{good_hours:4.1f}h  {bad_hours:4.1f}h   ║\n"
                )

            lines.append("╚" + "═" * 58 + "╝\n")
            lines.append("\n")

            # Calculate and add summary statistics
            avg_score = sum(d['posture_score'] for d in history) / len(history)
            best_day = max(history, key=lambda d: d['posture_score'])
            best_date = datetime.fromisoformat(best_day['date']).strftime('%a %m/%d')

            lines.append(f"Weekly Average: {avg_score:.1f}%\n")
            lines.append(f"Best Day: {best_date} ({best_day['posture_score']:.0f}%)\n")

            message = "".join(lines)
            self._show_message_box("7-Day Posture History", message)
            logger.info("7-day history displayed")

        except requests.RequestException as e:
            logger.error(f"Network error fetching history: {e}")
            self._show_message_box(
                "Connection Error",
                f"Cannot connect to DeskPulse backend.\n\n"
                f"Please check:\n"
                f"- Raspberry Pi is online\n"
                f"- Backend URL: {self.backend_url}\n\n"
                f"Error: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error displaying history: {e}")
            self._show_message_box(
                "Error",
                f"Failed to display history.\n\n"
                f"Error: {str(e)}"
            )

    def on_refresh_stats(self, icon, item):
        """
        Handle "View Stats → Refresh" menu selection.

        Forces immediate tooltip update from API and shows confirmation.
        Enterprise-grade: Shows user feedback with current stats.

        M2 fix: Rate limiting - 3 second cooldown to prevent API spam.
        """
        import time
        import requests

        # M2 fix: Rate limiting (3 second cooldown)
        now = time.time()
        if now - self._last_refresh_time < 3.0:
            logger.warning("Refresh stats rate limited (3s cooldown)")
            self._show_message_box(
                "Refresh Stats",
                "Please wait 3 seconds between refreshes.\n\n"
                "This prevents overloading the backend."
            )
            return

        logger.info("Stats manually refreshed from API")
        self._last_refresh_time = now

        try:
            # Fetch latest stats from API
            response = requests.get(
                f"{self.backend_url}/api/stats/today",
                timeout=5
            )

            if response.status_code != 200:
                self._show_message_box(
                    "Refresh Failed",
                    f"Failed to refresh stats from backend.\n\n"
                    f"Status: {response.status_code}\n"
                    f"Please check backend connection."
                )
                return

            stats = response.json()

            # Update tooltip with new data
            from app.windows_client.socketio_client import SocketIOClient
            if hasattr(self, 'socketio_client'):
                # Use existing update method
                self.socketio_client.tray_manager.update_tooltip(stats)

            # Show confirmation with current stats
            score = stats.get('posture_score', 0)
            good_mins = stats.get('good_duration_seconds', 0) / 60
            bad_mins = stats.get('bad_duration_seconds', 0) / 60
            total_events = stats.get('total_events', 0)

            # Visual indicator based on score
            if score >= 80:
                status_emoji = "✓ Excellent"
            elif score >= 60:
                status_emoji = "○ Good"
            else:
                status_emoji = "△ Needs Work"

            message = (
                f"╔═══════════════════════════════════════╗\n"
                f"║     STATS REFRESHED SUCCESSFULLY      ║\n"
                f"╚═══════════════════════════════════════╝\n\n"
                f"What This Does:\n"
                f"  • Forces immediate update of tray tooltip\n"
                f"  • Bypasses 60-second auto-refresh timer\n"
                f"  • Provides instant feedback on posture changes\n\n"
                f"─────────────────────────────────────────\n"
                f"Current Posture Score: {score:.0f}% {status_emoji}\n"
                f"─────────────────────────────────────────\n\n"
                f"Today's Session Summary:\n"
                f"  Good Posture:  {good_mins:>6.0f} minutes\n"
                f"  Bad Posture:   {bad_mins:>6.0f} minutes\n"
                f"  Total Events:  {total_events:>6}\n\n"
                f"✓ Tray icon tooltip updated with latest data"
            )

            self._show_message_box("Stats Refreshed", message)
            logger.info(f"Stats refreshed and displayed: {score:.0f}%")

        except requests.RequestException as e:
            logger.error(f"Network error refreshing stats: {e}")
            self._show_message_box(
                "Connection Error",
                f"Cannot connect to DeskPulse backend.\n\n"
                f"Please check:\n"
                f"- Raspberry Pi is online\n"
                f"- Backend URL: {self.backend_url}\n\n"
                f"Error: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Error refreshing stats: {e}")
            self._show_message_box(
                "Error",
                f"Failed to refresh stats.\n\n"
                f"Error: {str(e)}"
            )

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

            # Show MessageBox using helper (proper threading for tray)
            self._show_message_box("DeskPulse Settings", message)
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
                f"GitHub: https://github.com/EmekaOkaforTech/deskpulse.git\n"
                f"License: MIT"
            )

            # Show MessageBox using helper (proper threading for tray)
            self._show_message_box("About DeskPulse", message)
        except Exception as e:
            logger.exception(f"Error showing about: {e}")

    def on_uninstall(self, icon, item):
        """
        Handle "Uninstall DeskPulse" menu selection.

        Confirms uninstallation, then removes all files and settings.
        Only works for .exe installation, not source installation.
        """
        import os
        import shutil

        logger.info("Uninstall requested")

        # Confirm uninstallation using threaded dialog
        confirmed = self._show_yes_no_dialog(
            "Uninstall DeskPulse",
            "Are you sure you want to uninstall DeskPulse?\n\n"
            "This will remove:\n"
            "- DeskPulse application\n"
            "- All settings and config\n"
            "- Desktop and startup shortcuts\n\n"
            "This cannot be undone."
        )

        if not confirmed:
            logger.info("Uninstall cancelled by user")
            return

        logger.info("Uninstalling DeskPulse...")

        # Get installation directory (where DeskPulse is running from)
        install_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Disconnect and stop
        self.socketio_client.disconnect()
        if icon:
            icon.stop()

        # Flush logs before deletion
        for handler in logging.root.handlers:
            handler.flush()

        # Delete shortcuts (try multiple common locations)
        try:
            # Desktop shortcut (try both user profile methods)
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders')
            desktop_path = winreg.QueryValueEx(key, 'Desktop')[0]
            winreg.CloseKey(key)
            desktop_path = os.path.expandvars(desktop_path)

            desktop_shortcut = os.path.join(desktop_path, 'DeskPulse.lnk')
            if os.path.exists(desktop_shortcut):
                os.remove(desktop_shortcut)

            # Also try default location
            desktop_default = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop', 'DeskPulse.lnk')
            if os.path.exists(desktop_default):
                os.remove(desktop_default)

            # Startup shortcut
            startup = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows',
                                  'Start Menu', 'Programs', 'Startup', 'DeskPulse.lnk')
            if os.path.exists(startup):
                os.remove(startup)
        except Exception as e:
            logger.warning(f"Failed to remove shortcuts: {e}")

        # Delete config
        try:
            config_dir = os.path.join(os.environ['LOCALAPPDATA'], 'DeskPulse')
            if os.path.exists(config_dir):
                shutil.rmtree(config_dir)
        except Exception as e:
            logger.warning(f"Failed to remove config: {e}")

        # Create self-delete script (runs after Python exits)
        uninstall_script = os.path.join(os.environ['TEMP'], 'deskpulse_uninstall.bat')
        with open(uninstall_script, 'w') as f:
            f.write('@echo off\n')
            f.write('timeout /t 2 /nobreak >nul\n')
            f.write(f'rmdir /S /Q "{install_dir}"\n')
            f.write('del "%~f0"\n')

        # Show completion message
        self._show_message_box(
            "Uninstall Complete",
            f"DeskPulse has been uninstalled.\n\n"
            f"Installation folder will be removed:\n"
            f"{install_dir}\n\n"
            f"You can reinstall anytime from:\n"
            f"https://github.com/EmekaOkaforTech/deskpulse\n\n"
            f"Thank you for trying DeskPulse!"
        )

        # Launch self-delete script and exit
        import subprocess
        subprocess.Popen(
            ['cmd', '/c', uninstall_script],
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        # Exit application
        import sys
        sys.exit(0)

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
        Create enhanced context menu with View Stats submenu and Uninstall option.

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
        - Uninstall DeskPulse
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
            pystray.MenuItem("Uninstall DeskPulse", self.on_uninstall),
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
