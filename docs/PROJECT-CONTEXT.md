# DeskPulse Project Context & State

**Last Updated:** 2026-01-07
**Current Status:** Epic 8 (Standalone Windows) - Stories 8.1-8.2 Complete
**Critical:** READ THIS FIRST if resuming project

---

## CURRENT TASK (DO THIS NEXT)

**Epic 8, Story 8.3 & 8.4:** Create unified standalone Windows app
- Combine backend thread + tray UI in single process
- No SocketIO (local IPC only)
- File: `/app/standalone/__main__.py` (create this)
- Reference: `/app/standalone/backend_thread.py` (already done)
- Reference: `/app/windows_client/tray_manager.py` (reuse UI code)

---

## PROJECT OVERVIEW

**DeskPulse:** Posture monitoring system using camera + MediaPipe
- **Core Tech:** Raspberry Pi + camera + OpenCV + MediaPipe Pose
- **Backend:** Flask, SocketIO, SQLite
- **Frontend:** Web dashboard (Pico CSS)
- **Windows Client:** Python system tray app

**Business Model:** Open source (Pi version) + Commercial (Windows standalone)

---

## CRITICAL DECISIONS & RATIONALE

### 1. Open Source vs Commercial Split

**FREE (Open Source - GitHub):**
- Epics 1-4 (backend, monitoring, alerts, analytics)
- Raspberry Pi + camera required
- 7-day history limit
- **Why:** Builds credibility, serves makers/developers (5-10% of market)

**PAID (Commercial - £29 one-time):**
- Epic 7: Windows client for Pi (bonus - requires Pi)
- Epic 8: Standalone Windows (NO Pi needed) - **PRIMARY PRODUCT**
- Epic 9: Premium analytics (30-day history, exports, pain tracking)
- **Why:** Serves mainstream users (85-90% of market), no hardware needed

**Rationale:** Epic 8 (standalone) is the money-maker. Epic 7 (Pi client) is bonus. Separate audiences with fair value exchange.

---

### 2. Why Epic 8 Before Open Source Release?

**Original plan:** Release open source first (credibility) → then commercial
**Revised plan:** Build Epic 8 first → launch both simultaneously

**Why:**
- Epic 8 validates commercial model (most revenue)
- Open source release doesn't need Epic 5/6 (can launch with basic docs)
- Both launch Week 4 (open source + Pro same day)
- Faster time to market

---

### 3. Architecture: Standalone vs Client-Server

**Epic 7 (Windows Client - completed):**
- Client app on Windows
- Connects to Pi backend via SocketIO
- **Problem:** Still requires Pi ($50-80) + technical setup
- **Good for:** Existing Pi owners, tech enthusiasts (5% of paid market)

**Epic 8 (Standalone - in progress):**
- Backend + client in ONE .exe
- Uses PC webcam (DirectShow)
- No network, no SocketIO, no Pi
- **Good for:** Mainstream Windows users (90% of paid market)

**Both included in Pro (£29)** - customer chooses which to use.

---

## COMPLETED WORK

### Epic 1-4: Backend (Raspberry Pi) ✅
- Flask app with CV pipeline
- MediaPipe Pose detection
- Alert system (10-min threshold)
- SQLite analytics
- Web dashboard
- **Status:** Production-ready on Pi

### Epic 7: Windows Desktop Client ✅
- System tray integration (pystray)
- Toast notifications (win10toast)
- SocketIO client
- Professional teal icon (0,139,139 RGB)
- One-click installer (DeskPulse-Setup.exe - 27 MB)
- **Files:** `/app/windows_client/`, `/build/windows/`
- **Status:** Working, tested on Windows 10/11

### Epic 8, Story 8.1: Windows Backend Port ✅
- Configuration module: `/app/standalone/config.py`
  - %APPDATA%/DeskPulse paths
  - JSON config (not INI)
  - Rotating file logging
  - Pro features (30-day history)

- Flask modifications: `/app/__init__.py`
  - Added `standalone_mode` parameter
  - Skips SocketIO, Talisman, scheduler
  - Accepts custom database path

- Config class: `/app/config.py`
  - Added `StandaloneConfig` class
  - Windows defaults

### Epic 8, Story 8.2: Windows Camera ✅
- Camera module: `/app/standalone/camera_windows.py`
  - OpenCV with DirectShow backend
  - Camera detection (scans indices 0-5)
  - WindowsCamera class with context manager
  - Test functionality

- Backend thread: `/app/standalone/backend_thread.py`
  - Flask in background thread
  - CV pipeline with Windows camera
  - Status monitoring
  - Stats API access
  - Graceful shutdown

---

## IN PROGRESS

### Epic 8, Story 8.3-8.4: Unified Standalone App 🔄

**Goal:** Single .exe that runs backend + tray UI without network

**What's needed:**
1. Create `/app/standalone/__main__.py` - main entry point
2. Integrate `backend_thread.py` (already done)
3. Reuse tray UI from `/app/windows_client/tray_manager.py`
4. Replace SocketIO with direct function calls
5. Threading for backend (daemon) + tray (main thread)

**Architecture:**
```
DeskPulse-Standalone.exe
├─ Main Thread: TrayManager (UI)
└─ Background Thread: BackendThread
    ├─ Flask App (minimal, no web server needed)
    ├─ CV Pipeline (posture monitoring)
    ├─ WindowsCamera (DirectShow)
    ├─ Alert Manager
    └─ SQLite (%APPDATA%)

Communication: Direct function calls (no SocketIO)
- Backend exposes: get_status(), pause_monitoring(), resume_monitoring(), get_stats()
- Tray calls directly: backend.pause_monitoring()
```

---

## PENDING WORK

### Epic 8, Story 8.5: All-in-One Installer 📋
- PyInstaller spec for standalone
- Bundle everything in one .exe
- ~40-50 MB (includes Python runtime)
- Auto-start with Windows
- Professional installer experience

### Epic 9: Premium Analytics 📋
- 30+ day history (vs 7-day free)
- Pain tracking
- Pattern detection
- CSV/PDF exports
- **Timeline:** After Epic 8 launch

### Open Source Release 📋
- Create `open-source-v1.0` branch
- Remove `/app/windows_client/`, `/app/standalone/`, `/build/windows/`
- Update README for Pi-only audience
- Push to GitHub (public)
- **Timeline:** Week 4 (same as Pro launch)

---

## KEY FILE LOCATIONS

### Standalone Windows (Epic 8 - In Progress)
```
/app/standalone/
├── __init__.py                  ✅ Created
├── config.py                    ✅ Windows config, paths, logging
├── camera_windows.py            ✅ DirectShow camera capture
├── backend_thread.py            ✅ Flask in background thread
├── __main__.py                  ⏳ TODO - Main entry point
└── tray_app.py                  ⏳ TODO - Reuse Epic 7 tray code

/build/windows/standalone/       ⏳ TODO - Build scripts
├── build_standalone.bat
├── standalone.spec
└── installer_standalone.py
```

### Windows Client (Epic 7 - Complete)
```
/app/windows_client/
├── __main__.py                  ✅ Entry point
├── config.py                    ✅ Client config
├── tray_manager.py              ✅ System tray UI (REUSE in Epic 8)
├── notifier.py                  ✅ Toast notifications (REUSE)
├── socketio_client.py           ✅ SocketIO (NOT NEEDED in Epic 8)

/build/windows/
├── build_complete_installer.bat ✅ Epic 7 installer builder
├── installer_wrapper.py         ✅ Epic 7 installer script
└── deskpulse_client.spec        ✅ PyInstaller spec for Epic 7
```

### Backend (Shared - Raspberry Pi & Standalone)
```
/app/
├── __init__.py                  ✅ Modified for standalone_mode
├── config.py                    ✅ Added StandaloneConfig
├── cv/pipeline.py               ✅ CV processing
├── cv/capture.py                ✅ Pi camera (not used in Epic 8)
├── main/routes.py               ✅ Web routes
├── api/routes.py                ✅ REST API
├── data/analytics.py            ✅ Analytics engine
```

### Documentation
```
/docs/
├── OPEN-SOURCE-STRATEGY.md      ✅ Complete strategy document
├── PROJECT-CONTEXT.md           ✅ THIS FILE
├── epics.md                     ✅ Updated with Epic 8, 9
├── sprint-artifacts/
    ├── epic-7-windows-desktop-client.md          ✅ Complete
    ├── epic-8-standalone-windows.md              ✅ Created
    ├── story-8-1-windows-backend-port.md         ✅ Complete
    └── validation-report-*.md                    ✅ Multiple stories
```

---

## DEPENDENCIES & TECH STACK

### Backend (Shared)
- Flask 2.3+
- OpenCV 4.8+ (cv2)
- MediaPipe 0.10+
- SQLite (built-in)
- python-socketio (Pi mode only)

### Windows Standalone (Epic 8)
- opencv-python (DirectShow backend)
- pystray (system tray)
- Pillow (icon generation)
- win32toast (notifications - reuse from Epic 7)
- PyInstaller (build .exe)
- **No SocketIO, no flask-socketio**

### Windows Client (Epic 7 - for Pi)
- python-socketio
- requests
- pystray, Pillow, win32toast
- PyInstaller

---

## BUILD & TEST COMMANDS

### Test Standalone Components (Linux/Pi development)
```bash
# Test Windows config module
python -m app.standalone.config

# Test Windows camera module (requires Windows)
python -m app.standalone.camera_windows

# Test backend thread (requires Windows)
python -m app.standalone.backend_thread
```

### Build Epic 7 Installer (Windows Client - already works)
```powershell
cd C:\deskpulse-build\deskpulse_installer
.\build\windows\build_complete_installer.bat
# Output: dist\DeskPulse-Setup.exe (27 MB)
```

### Build Epic 8 Installer (Standalone - TODO)
```powershell
cd C:\deskpulse-build\deskpulse_installer
.\build\windows\standalone\build_standalone.bat
# Output: dist\DeskPulse-Standalone.exe (40-50 MB)
```

---

## GIT REPOSITORY STRATEGY

### Gitea (Private - Full Version)
- **URL:** `192.168.10.126:Emeka/deskpulse.git`
- **Contains:** ALL code (open source + Pro)
- **Branches:** `master` (main development)
- **Tags:** `v1.0.0` (Epic 7 complete)
- **Purpose:** Source of truth, full development history

### GitHub (Public - Open Source Only)
- **URL:** `github.com/[username]/deskpulse` (to be created)
- **Branch:** `open-source-v1.0` (clean branch, no Windows code)
- **Contains:** Epics 1-4 only (Pi backend)
- **License:** MIT or GPL-3.0
- **Purpose:** Open source distribution, community

**Process:**
1. Create `open-source-v1.0` branch from master
2. Remove `/app/windows_client/`, `/app/standalone/`, `/build/windows/`
3. Update README for Pi-only audience
4. Push to GitHub (new public repo)
5. Gitea remains full version (private)

---

## YOUTUBE MARKETING STRATEGY

### Video 1: Open Source (Week 4-5)
- "I Built an Open Source Posture Monitor with Raspberry Pi"
- 10-12 minutes
- Target: Makers, developers
- Goal: GitHub stars, credibility

### Video 2: Pro Launch (Week 4-5)
- "Why I Built a Windows Version"
- 8-10 minutes
- Target: Professionals, office workers
- Goal: Pro sales, explain value

### Video 3: Results (Week 6-8)
- "30 Days of Posture Tracking - Real Results"
- 12-15 minutes
- Target: Potential Pro customers
- Goal: Show ROI, validate pricing

---

## PRICING & POSITIONING

**Free (Open Source):**
- Raspberry Pi + camera required
- 7-day history
- Web dashboard
- Self-hosted, zero cloud
- **Price:** FREE
- **Target:** 5-10% of users (makers)

**Pro (Commercial):**
- Includes BOTH:
  1. DeskPulse Standalone (Epic 8) - NO Pi needed
  2. DeskPulse Pi Client (Epic 7) - Bonus for Pi owners
- 30-day history
- Premium analytics (Epic 9)
- Email support
- **Price:** £29 one-time OR £5/month
- **Target:** 85-90% of users (mainstream)

**Future: Mac Pro:**
- Epic 8b (standalone Mac)
- Same £29 price
- **Target:** 5-10% of users (Mac)

---

## COMMON MISTAKES TO AVOID

1. **Don't rebuild Epic 5/6 before launch** - Not required, deferred
2. **Don't add SocketIO to Epic 8** - Use direct function calls only
3. **Don't mix Epic 7 and Epic 8 code** - Separate directories
4. **Don't forget standalone_mode=True** - Required in create_app()
5. **Don't use systemd in Windows** - Use background threads
6. **Don't hardcode paths** - Use %APPDATA% via config module
7. **Don't build installer before Stories 8.3-8.5 complete** - Backend must work first

---

## CRITICAL PATHS & CONTEXT

### Path: %APPDATA%/DeskPulse
```
C:\Users\[username]\AppData\Roaming\DeskPulse\
├── config.json                   # User configuration
├── deskpulse.db                  # SQLite database
└── logs\
    └── deskpulse.log             # Application logs (rotating)
```

### Environment: Windows Development
- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11+ (for type hints)
- **Webcam:** DirectShow compatible
- **Build:** PyInstaller 6.0+

### Environment: Raspberry Pi Production
- **OS:** Raspberry Pi OS (Bookworm)
- **Python:** 3.11
- **Camera:** Pi Camera Module v2 or USB webcam
- **Service:** systemd

---

## TROUBLESHOOTING CONTEXT

### Issue: "ModuleNotFoundError: No module named 'flask_talisman'"
**Solution:** You're importing `app.__init__.py` in standalone mode. Ensure `standalone_mode=True` is passed to `create_app()`.

### Issue: "Camera not found" on Windows
**Solution:** Check DirectShow backend: `cv2.VideoCapture(0, cv2.CAP_DSHOW)`. Test with `/app/standalone/camera_windows.py`.

### Issue: "SocketIO not initialized"
**Solution:** In standalone mode, SocketIO is skipped. Don't call `socketio.emit()`. Use direct function calls.

### Issue: PyInstaller .exe crashes immediately
**Solution:** Run from command line to see errors: `.\DeskPulse-Standalone.exe`. Check logs in `%APPDATA%/DeskPulse/logs/`.

---

## NEXT SESSION CHECKLIST

If resuming this project in a new session:

1. **Read this document first** - Critical context
2. **Check todo list** - Current tasks
3. **Read `/docs/OPEN-SOURCE-STRATEGY.md`** - Business model
4. **Read `/docs/sprint-artifacts/epic-8-standalone-windows.md`** - Technical details
5. **Check git status** - Uncommitted changes
6. **Review last commit** - `git log -1 --stat`
7. **Continue from Story 8.3-8.4** - Create unified standalone app

---

## CONTACT & HANDOFF

**Project Owner:** okafor_dev
**Repository:** Gitea: `192.168.10.126:Emeka/deskpulse.git`
**Development Machine:** Raspberry Pi (backend) + Windows PC (client testing)
**Key Decisions Documented:** `/docs/OPEN-SOURCE-STRATEGY.md`

**If starting new session:**
- Agent should ask: "Continuing Epic 8 Story 8.3-8.4 (unified standalone app)?"
- Agent should confirm: "I've read PROJECT-CONTEXT.md, ready to continue"

---

**END OF CONTEXT DOCUMENT**

Last updated: 2026-01-07 by Claude Sonnet 4.5
Next update: After Story 8.5 complete (Epic 8 done)
