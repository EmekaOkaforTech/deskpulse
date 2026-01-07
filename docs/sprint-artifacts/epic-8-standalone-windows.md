# Epic 8: Standalone Windows Edition

**Epic ID:** Epic-8
**Status:** In Progress
**Started:** 2026-01-07
**Target:** Mainstream Windows users (no Pi needed)

---

## Epic Goal

Create standalone Windows application that runs DeskPulse entirely on Windows PC using built-in/USB webcam, eliminating need for Raspberry Pi hardware.

---

## User Value

Non-technical Windows users get complete posture monitoring with one installer - no hardware purchase, no network setup, no browser tabs needed.

---

## User Story

**As a** Windows office worker
**I want** posture monitoring on my PC without buying Raspberry Pi
**So that** I can improve my posture with minimal setup effort

---

## Acceptance Criteria

- [ ] Single installer: DeskPulse-Standalone.exe
- [ ] Uses Windows PC webcam (DirectShow)
- [ ] No Raspberry Pi required
- [ ] No network configuration needed
- [ ] System tray integration
- [ ] Toast notifications
- [ ] 30-day analytics
- [ ] Auto-starts with Windows
- [ ] Complete uninstall cleanup
- [ ] Works on clean Windows 10/11

---

## Architecture Changes

### Current Architecture (Pi + Windows Client)
```
Raspberry Pi                    Windows PC
├─ Flask Backend                ├─ Windows Client
├─ Camera (Pi Cam/USB)          ├─ SocketIO connection
├─ OpenCV Processing            ├─ System Tray
├─ SQLite Database              └─ Toast Notifications
├─ SocketIO Server
└─ Web Dashboard
        ↓ (Network)
    Windows Client
```

### New Architecture (Standalone Windows)
```
Windows PC
├─ DeskPulse-Standalone.exe
    ├─ Flask Backend (embedded)
    ├─ Camera (DirectShow)
    ├─ OpenCV Processing
    ├─ SQLite Database
    ├─ System Tray UI
    ├─ Toast Notifications
    └─ Web Dashboard (optional)

All in ONE process, NO network
```

---

## Technical Approach

### Single-Process Architecture
- Backend runs in background thread
- Tray UI runs in main thread
- Direct function calls (no SocketIO)
- Shared memory/queues for IPC
- SQLite in %APPDATA%/DeskPulse

### Windows Integration
- Background process (not Windows Service for simplicity)
- Registry for auto-start
- %APPDATA% for config/database
- Windows webcam APIs (DirectShow via OpenCV)
- Native Windows notifications

---

## Stories

### Story 8.1: Windows Backend Port ✅ In Progress
**Goal:** Flask backend runs on Windows with local config

**Tasks:**
- Windows-compatible file paths (%APPDATA%)
- Configuration without systemd
- Windows camera support in capture module
- Background process wrapper
- Logging to file (not systemd journal)

**Acceptance:**
- Backend starts on Windows
- Uses Windows webcam
- Logs to %APPDATA%/DeskPulse/logs
- Config in %APPDATA%/DeskPulse/config.json

---

### Story 8.2: Windows Camera Capture
**Goal:** OpenCV captures from Windows webcam (DirectShow)

**Tasks:**
- DirectShow backend for OpenCV
- Camera selection dialog
- Camera permission handling
- Fallback for generic USB cameras
- Multi-camera support

**Acceptance:**
- Detects Windows webcams
- Captures video frames
- Works with built-in + USB cameras
- Graceful degradation if no camera

---

### Story 8.3: Local Architecture (Remove SocketIO)
**Goal:** Backend and client communicate without network

**Tasks:**
- Replace SocketIO with threading queues
- Direct function calls for alerts
- Shared state management
- Event system for notifications
- Remove Flask-SocketIO dependency

**Acceptance:**
- No network ports used
- Notifications work without SocketIO
- Alerts trigger directly
- Stats API works locally

---

### Story 8.4: Unified System Tray Application
**Goal:** Single executable with backend + tray UI

**Tasks:**
- Reuse Epic 7 tray manager code
- Integrate backend as thread
- Local notification delivery
- Dashboard opens localhost (embedded server)
- Menu controls call backend directly

**Acceptance:**
- Single .exe runs everything
- Tray icon shows status
- All menu options work
- No external dependencies

---

### Story 8.5: All-in-One Installer
**Goal:** DeskPulse-Standalone-Setup.exe installs everything

**Tasks:**
- PyInstaller spec for combined app
- Installer creates shortcuts
- Auto-start configuration
- Uninstaller cleanup
- Icon bundling

**Acceptance:**
- Single installer .exe (~40-50 MB)
- Double-click install
- Auto-starts with Windows
- Clean uninstall
- Professional UX

---

## Dependencies

**Reused from Epic 7:**
- System tray UI (`app/windows_client/tray_manager.py`)
- Toast notifications (`app/windows_client/notifier.py`)
- Icon assets (`assets/windows/icon_professional.ico`)

**Modified from Backend:**
- Flask app (embedded, no systemd)
- CV pipeline (DirectShow cameras)
- Alert manager (direct calls, no SocketIO)
- Analytics engine (reused as-is)

**New Components:**
- Windows configuration module
- Background thread manager
- Local IPC mechanism
- Unified launcher

---

## File Structure

```
app/
├─ standalone/                    # NEW - Standalone Windows edition
│   ├─ __init__.py
│   ├─ __main__.py               # Entry point
│   ├─ config.py                 # Windows config (%APPDATA%)
│   ├─ backend_thread.py         # Flask in background thread
│   ├─ tray_app.py               # Tray UI (reuse Epic 7)
│   ├─ local_events.py           # IPC (replace SocketIO)
│   └─ camera_windows.py         # DirectShow camera capture
├─ windows_client/               # Epic 7 - Pi client (bonus)
├─ main/                         # Backend (shared)
├─ api/                          # Backend (shared)
├─ cv/                           # Backend (shared)
└─ ...

build/
└─ windows/
    ├─ standalone/               # NEW - Epic 8 build scripts
    │   ├─ build_standalone.bat
    │   ├─ standalone.spec
    │   └─ installer_standalone.py
    └─ client/                   # Epic 7 build scripts
```

---

## Testing Strategy

### Manual Testing Checklist
- [ ] Install on clean Windows 10
- [ ] Install on clean Windows 11
- [ ] Test with built-in webcam
- [ ] Test with USB webcam
- [ ] Test with no webcam (graceful degradation)
- [ ] Auto-start after reboot
- [ ] Uninstall removes all files
- [ ] No leftover registry keys
- [ ] Works offline (no network)
- [ ] Multiple monitors
- [ ] High DPI displays

### Automated Testing
- Unit tests for Windows config
- Camera detection tests (mocked)
- IPC event tests
- Alert manager tests (local mode)

---

## Timeline

**Week 1:**
- Story 8.1: Windows backend port (3 days)
- Story 8.2: Camera capture (2 days)

**Week 2:**
- Story 8.3: Local architecture (3 days)
- Story 8.4: Unified app (2 days)

**Week 3:**
- Story 8.5: Installer (2 days)
- Testing and refinement (3 days)

**Total: 15 working days (~3 weeks)**

---

## Success Metrics

**Technical:**
- Installer size: <50 MB
- Startup time: <3 seconds
- Memory usage: <200 MB
- CPU usage: <10% (monitoring)
- Camera FPS: 5-10 (configurable)

**User Experience:**
- Install to monitoring: <60 seconds
- Zero configuration needed
- Professional, polished UX
- No crashes in 8-hour session

---

## Risks & Mitigations

**Risk:** Windows Defender flags .exe as suspicious
**Mitigation:** Code signing certificate ($200/year)

**Risk:** Camera permissions blocked by default
**Mitigation:** Clear permission dialog, documentation

**Risk:** High CPU usage on low-end PCs
**Mitigation:** Configurable FPS, quality settings

**Risk:** PyInstaller bundle too large
**Mitigation:** Exclude unused dependencies, UPX compression

---

## Related Documents

- `/docs/OPEN-SOURCE-STRATEGY.md` - Overall product strategy
- `/docs/sprint-artifacts/epic-7-windows-desktop-client.md` - Pi client (bonus)
- `/docs/Architecture.md` - Backend architecture
- `/build/windows/standalone/` - Build scripts

---

**Epic Owner:** Development Team
**Target Release:** v2.0.0 (Pro Standalone Edition)
