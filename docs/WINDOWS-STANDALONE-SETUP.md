# Windows Standalone Setup Guide

**Status:** Story 8.1 Implementation Phase
**Last Updated:** 2026-01-07

## Overview

DeskPulse Standalone Edition runs entirely on Windows without requiring Raspberry Pi hardware. The backend runs in a background thread using Windows camera and %APPDATA% storage.

---

## System Requirements

- **Operating System:** Windows 10/11 (64-bit)
- **Python:** 3.11 or higher
- **Camera:** Built-in or USB webcam with Windows camera permissions
- **RAM:** 4GB+ recommended
- **Disk Space:** 500MB for application and logs
- **Permissions:** Camera access, file system access to %APPDATA%

---

## Installation (Development - Story 8.1)

### Prerequisites

1. **Install Python 3.11+**
   - Download from: https://www.python.org/downloads/windows/
   - ✅ Check "Add Python to PATH" during installation
   - Verify: `python --version` (should show 3.11+)

2. **Install Git for Windows**
   - Download from: https://git-scm.com/download/win
   - Use default settings

### Setup Steps

```bash
# 1. Clone repository
git clone https://github.com/yourusername/deskpulse.git
cd deskpulse

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify installation
python -m app.standalone.config
```

---

## Running the Backend

### Basic Usage

```bash
# Activate virtual environment (if not already active)
venv\Scripts\activate

# Run backend (console mode for development)
python -m app.standalone.backend_thread
```

The backend will:
- Create config in `%APPDATA%\DeskPulse\config.json`
- Initialize database at `%APPDATA%\DeskPulse\deskpulse.db`
- Start camera monitoring
- Log to `%APPDATA%\DeskPulse\logs\deskpulse.log`

### Expected Startup

```
INFO - deskpulse.standalone.config - DeskPulse Standalone v2.0.0 starting
INFO - deskpulse.standalone.config - Data directory: C:/Users/YourName/AppData/Roaming/DeskPulse
INFO - deskpulse.standalone.backend - Backend thread started
INFO - deskpulse.standalone.backend - Database initialized: C:/Users/YourName/AppData/Roaming/DeskPulse/deskpulse.db
INFO - deskpulse.standalone.backend - CV pipeline started
```

---

## Configuration

### Config File Location

`%APPDATA%\DeskPulse\config.json`

**Example:** `C:/Users/YourName/AppData/Roaming/DeskPulse/config.json`

### Default Configuration

```json
{
  "camera": {
    "index": 0,
    "fps": 10,
    "width": 640,
    "height": 480,
    "backend": "directshow"
  },
  "monitoring": {
    "alert_threshold_seconds": 600,
    "detection_interval_seconds": 1,
    "enable_notifications": true
  },
  "analytics": {
    "history_days": 30,
    "enable_exports": true
  },
  "ui": {
    "start_minimized": false,
    "show_dashboard_on_start": false,
    "enable_toast_notifications": true
  },
  "advanced": {
    "log_level": "INFO",
    "enable_debug": false,
    "camera_warmup_seconds": 2
  }
}
```

### Configuration Options

**Camera Settings:**
- `index`: Camera device index (0 for default, 1+ for additional cameras)
- `fps`: Frames per second for posture detection (10 recommended)
- `width` / `height`: Camera resolution
- `backend`: "directshow" for Windows cameras

**Monitoring Settings:**
- `alert_threshold_seconds`: Time in seconds before bad posture alert (default: 600 = 10 minutes)
- `detection_interval_seconds`: How often to check posture
- `enable_notifications`: Enable/disable desktop notifications

**Advanced Settings:**
- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `enable_debug`: Additional debug output

---

## Troubleshooting

### Camera Not Opening

**Symptoms:**
- "Failed to open camera" error
- Backend stops after starting

**Solutions:**

1. **Check Camera Permissions**
   ```
   Settings → Privacy & Security → Camera
   → Allow apps to access camera: ON
   → Allow Python.exe or DeskPulse.exe: ON
   ```

2. **Try Different Camera Index**
   - Edit config.json: `"index": 1` or `"index": 2`
   - Multiple webcams may use different indices

3. **Test Camera with Windows Camera App**
   - Open Windows Camera app
   - Verify camera works
   - Close Camera app before running DeskPulse

4. **Check for Camera Conflicts**
   - Close other apps using camera (Zoom, Teams, etc.)
   - Only one app can use camera at a time

### Database Errors

**Symptoms:**
- "Cannot create database file" error
- Permission denied errors

**Solutions:**

1. **Check Antivirus/Windows Defender**
   ```
   Windows Security → Virus & threat protection
   → Exclusions → Add folder
   → Add: %APPDATA%\DeskPulse
   ```

2. **Verify Disk Space**
   - Ensure at least 500MB free on C: drive

3. **Check File Permissions**
   - Ensure user has write access to %APPDATA%

### Long Path Issues (Rare)

**Symptoms:**
- "Path too long" error on older Windows versions

**Solution:**
- Enable long path support:
  ```
  Registry: HKLM\SYSTEM\CurrentControlSet\Control\FileSystem
  Set LongPathsEnabled = 1
  ```
- Or use shorter Windows username

### OneDrive Synced AppData (Enterprise Users)

**Symptoms:**
- Database conflicts across multiple devices
- Sync issues

**Solution:**
- Use local %LOCALAPPDATA% instead (requires code change)
- Or exclude DeskPulse folder from OneDrive sync

### Logging Issues

**Check Logs:**
```
notepad %APPDATA%\DeskPulse\logs\deskpulse.log
```

**Increase Log Detail:**
Edit config.json:
```json
{
  "advanced": {
    "log_level": "DEBUG"
  }
}
```

---

## File Locations

| Item | Location | Typical Path |
|------|----------|--------------|
| Config | `%APPDATA%\DeskPulse\config.json` | `C:/Users/You/AppData/Roaming/DeskPulse/config.json` |
| Database | `%APPDATA%\DeskPulse\deskpulse.db` | `C:/Users/You/AppData/Roaming/DeskPulse/deskpulse.db` |
| Logs | `%APPDATA%\DeskPulse\logs\deskpulse.log` | `C:/Users/You/AppData/Roaming/DeskPulse/logs/deskpulse.log` |
| WAL Files | `%APPDATA%\DeskPulse\deskpulse.db-wal` | (Auto-created for database durability) |

---

## Testing

### Run Unit Tests

```bash
# Activate virtual environment
venv\Scripts\activate

# Run all standalone tests
pytest tests/test_standalone_config.py tests/test_backend_thread.py -v

# Run specific test
pytest tests/test_standalone_config.py::TestPathFunctions -v
```

### Manual Testing Checklist

- [ ] Backend starts without errors
- [ ] Camera opens and displays frames
- [ ] Database file created in %APPDATA%
- [ ] Logs written to log file
- [ ] Posture detection runs (check logs)
- [ ] Config changes persist after restart
- [ ] Works with non-ASCII username (if applicable)
- [ ] Graceful shutdown with Ctrl+C

---

## Known Limitations (Story 8.1)

This is the backend implementation only. The following features come in later stories:

- ❌ **No System Tray UI** (Story 8.4)
- ❌ **No Camera Selection Dialog** (Story 8.2)
- ❌ **No Installer** (Story 8.5)
- ❌ **No Local IPC** (Story 8.3 - currently uses backend thread directly)
- ❌ **Console-only** (GUI in Story 8.4)

**Current Capabilities:**
- ✅ Backend runs on Windows
- ✅ Windows camera capture
- ✅ Posture monitoring
- ✅ Database persistence with WAL mode
- ✅ File-based logging
- ✅ Configuration management
- ✅ Analytics calculations

---

## Development

### Project Structure

```
app/standalone/
├── config.py           # Windows configuration (paths, settings)
├── backend_thread.py   # Background thread wrapper
└── camera_windows.py   # Windows camera (DirectShow)
```

### Running Tests

```bash
# Unit tests (fast, mocked)
pytest tests/test_standalone_config.py -v
pytest tests/test_backend_thread.py -v

# Integration tests (slower, real database)
pytest tests/test_standalone_integration.py -v

# All tests
pytest tests/test_standalone*.py -v
```

### Code Quality

```bash
# Lint code
flake8 app/standalone/

# Type checking (if mypy configured)
mypy app/standalone/
```

---

## Next Steps

1. **Story 8.2:** Windows camera selection UI and permission handling
2. **Story 8.3:** Local IPC to replace network SocketIO
3. **Story 8.4:** Unified system tray application
4. **Story 8.5:** PyInstaller all-in-one .exe installer

---

## Support

**Documentation:** See `/docs/architecture.md` for system design
**Issues:** https://github.com/yourusername/deskpulse/issues
**Story:** `/docs/sprint-artifacts/8-1-windows-backend-port.md`

---

**Implementation Status:** ✅ Backend Complete, Testing on Windows Required
**Tests:** 58/68 passing (85%), 3 production bugs fixed
**Next:** Windows hardware validation (Tasks 1-3)
