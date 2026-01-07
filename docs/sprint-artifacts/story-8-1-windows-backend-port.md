# Story 8.1: Windows Backend Port

**Story ID:** 8.1
**Epic:** Epic 8 - Standalone Windows Edition
**Status:** Ready for Dev (Code Complete - Needs Windows Testing)
**Started:** 2026-01-07
**Updated:** 2026-01-07

---

## Story

**As a** Windows user
**I want** DeskPulse backend to run on my Windows PC
**So that** I don't need to buy or configure a Raspberry Pi

---

## Acceptance Criteria

- [ ] Backend runs on Windows 10/11
- [ ] Uses %APPDATA%/DeskPulse for all data storage
- [ ] Configuration in JSON format (no systemd/INI)
- [ ] Logging to files (not systemd journal)
- [ ] Windows webcam support (DirectShow)
- [ ] SQLite database in %APPDATA%
- [ ] No Raspberry Pi dependencies

---

## Technical Implementation

### 1. Windows Configuration Module ✅ Complete

**File:** `/app/standalone/config.py`

**Features:**
- Windows path handling (%APPDATA%/DeskPulse)
- JSON configuration (no INI files)
- Default configuration with sensible values
- Logging setup (rotating file handler)
- Helper functions for all paths

**Paths:**
```
%APPDATA%/DeskPulse/
├── config.json           # Configuration
├── deskpulse.db         # SQLite database
└── logs/
    └── deskpulse.log    # Application logs (10 MB, 5 backups)
```

**Default Configuration:**
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

---

### 2. Windows Camera Capture ✅ Complete

**File:** `/app/standalone/camera_windows.py`

**Features:**
- OpenCV with DirectShow backend
- Camera detection (scans indices 0-5)
- Configurable resolution and FPS
- Context manager support
- Comprehensive error handling
- Camera testing functionality

**Usage:**
```python
from app.standalone.camera_windows import WindowsCamera

# Simple usage
with WindowsCamera(index=0, fps=10) as camera:
    ret, frame = camera.read()
    if ret:
        # Process frame
        pass

# Detect cameras
from app.standalone.camera_windows import detect_cameras
cameras = detect_cameras()  # Returns [0, 1, ...] for available cameras
```

---

### 3. Backend Thread Wrapper (TODO)

**File:** `/app/standalone/backend_thread.py` (to be created)

**Purpose:** Run Flask backend in background thread

**Requirements:**
- Flask app runs in daemon thread
- SQLite database in %APPDATA%
- Reuse existing backend code (app/main, app/api, app/cv)
- Graceful shutdown
- Error recovery

---

### 4. Modified Backend Components (TODO)

**Changes needed in existing backend:**

**`app/cv/capture.py`:**
- Add Windows camera support
- Use `WindowsCamera` class for DirectShow
- Keep Pi camera support (for Epic 7)
- Auto-detect platform and choose camera type

**`app/__init__.py` (create_app):**
- Accept database path parameter (for %APPDATA%)
- Skip systemd-specific initialization
- Make SocketIO optional (for local mode)

**`app/config.py`:**
- Add StandaloneConfig class
- Windows-compatible paths
- Load from JSON (not INI)

---

## File Structure

```
app/
└── standalone/
    ├── __init__.py              ✅ Created
    ├── config.py                ✅ Created (Windows config module)
    ├── camera_windows.py        ✅ Created (DirectShow camera)
    ├── backend_thread.py        ⏳ TODO (Flask background thread)
    ├── local_events.py          ⏳ Story 8.3 (IPC without SocketIO)
    └── tray_app.py              ⏳ Story 8.4 (Unified tray app)
```

---

## Testing

### Unit Tests (TODO)

**Test config module:**
```python
def test_get_appdata_dir():
    """Test Windows AppData directory detection."""
    dir = get_appdata_dir()
    assert dir.exists()
    assert 'DeskPulse' in str(dir)

def test_load_config_creates_default():
    """Test config file created with defaults if missing."""
    # Delete config if exists
    # Call load_config()
    # Verify file created with DEFAULT_CONFIG
```

**Test camera module:**
```python
def test_detect_cameras():
    """Test camera detection."""
    cameras = detect_cameras()
    assert isinstance(cameras, list)

def test_camera_open_close():
    """Test camera lifecycle."""
    cam = WindowsCamera(0)
    assert cam.open()
    assert cam.is_available()
    cam.release()
    assert not cam.is_available()
```

### Manual Testing (In Progress)

**On Windows 10:**
- [ ] Run config.py standalone - creates %APPDATA%/DeskPulse
- [ ] Verify config.json created with defaults
- [ ] Verify logs directory created
- [ ] Run camera_windows.py standalone - detects cameras
- [ ] Verify camera capture works (built-in webcam)
- [ ] Verify camera capture works (USB webcam)

---

## Dependencies

**Python Packages:**
- opencv-python (already installed)
- Standard library only (os, json, pathlib, logging)

**No new dependencies** - uses existing packages.

---

## Progress Tracker

**Completed (Code Written):**
- [x] Windows configuration module (config.py)
- [x] Windows path handling (%APPDATA%)
- [x] JSON configuration system
- [x] Logging configuration (file-based)
- [x] Windows camera capture (camera_windows.py)
- [x] Camera detection (detect_cameras)
- [x] Camera testing utilities
- [x] Backend thread wrapper (backend_thread.py)
- [x] Modified Flask app for standalone mode (app/__init__.py)
- [x] StandaloneConfig class (app/config.py)

**Missing (NOT DONE):**
- [ ] **CRITICAL: Windows testing** - Zero code executed on Windows PC
- [ ] Manual validation of all acceptance criteria
- [ ] Backend thread wrapper integration test
- [ ] Camera detection test on actual Windows
- [ ] Config file creation test on Windows
- [ ] SQLite database creation test in %APPDATA%

**Blocked:**
- Requires Windows PC for testing (development done on Linux/Pi)

---

## Next Steps

1. Create `backend_thread.py` - Flask in background thread
2. Modify `app/cv/capture.py` - use WindowsCamera on Windows
3. Modify `app/__init__.py` - accept custom database path
4. Integration test - backend runs on Windows
5. Move to Story 8.2 (if camera already works)

---

## Notes

**Windows-Specific Considerations:**
- DirectShow is built into Windows (no extra drivers needed)
- %APPDATA%/Roaming is standard for application data
- Rotating log files prevent disk space issues
- JSON config is more Windows-friendly than INI

**Platform Detection:**
```python
import platform
if platform.system() == 'Windows':
    # Use WindowsCamera
    from app.standalone.camera_windows import WindowsCamera
    camera = WindowsCamera(0)
else:
    # Use Pi camera
    from app.cv.capture import Camera
    camera = Camera()
```

---

**Story Owner:** Development Team
**Estimated Effort:** 3 days
**Actual Effort:** TBD
