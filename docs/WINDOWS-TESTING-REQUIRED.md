# Windows Testing Requirements - Story 8.1

**Status:** ⚠️ **BLOCKING - Required Before Story Completion**
**Created:** 2026-01-07
**Code Review:** Automated fixes applied, Windows validation pending

---

## Overview

Story 8.1 code is **95% complete** with all unit tests passing on Linux. However, **Windows-specific validation is REQUIRED** before marking the story as complete per enterprise requirements and Definition of Done.

---

## ✅ COMPLETED (On Linux)

- ✅ All 73 unit/integration tests passing
- ✅ Config merge bug fixed (deep merge implemented)
- ✅ Test coverage measured: 90% config.py, 77% backend_thread.py
- ✅ Thread safety stress tests added
- ✅ WAL checkpoint on shutdown implemented
- ✅ Backend timeout increased to 15 seconds
- ✅ Error handling improved
- ✅ Code review issues #2-#13 addressed

---

## ⚠️ BLOCKING REQUIREMENTS (Windows Testing)

These tasks **MUST** be completed on actual Windows 10/11 hardware:

### Issue #1: Windows Validation (CRITICAL - Story DoD)

**Location:** Story Task 1, Task 2
**Estimated Time:** 6-8 hours first time, 2-3 hours subsequent

#### Required Setup:

**Option A: Windows VM (Recommended)**
```bash
# 1. Download Windows 10/11 VM
https://developer.microsoft.com/windows/downloads/virtual-machines/

# 2. Install VirtualBox or VMware
# 3. Configure VM:
- 4GB+ RAM
- 50GB+ disk
- USB passthrough (for webcam)
- Shared folder with deskpulse repo

# 4. In VM - Setup environment
- Install Python 3.11: https://www.python.org/downloads/windows/
- Install Git for Windows
- Clone repo or use shared folder
- Create venv: python -m venv venv
- Install deps: venv\Scripts\pip install -r requirements.txt
```

**Option B: Actual Windows Hardware**
- Windows 10/11 PC with webcam
- Same Python/Git setup as Option A

#### Required Validation Tests:

**1. Configuration Module (app/standalone/config.py)**
```powershell
# Test 1: Verify config creation
python -m app.standalone.config

# Expected output:
# - Config file created at %APPDATA%\DeskPulse\config.json
# - Log directory created at %APPDATA%\DeskPulse\logs\
# - Database path shows correct Windows location

# Verify manually:
dir %APPDATA%\DeskPulse\
type %APPDATA%\DeskPulse\config.json

# Test 2: Non-ASCII username paths
# Create test user with non-ASCII name (José, München, etc.)
# Run config test as that user
```

**2. Camera Module (app/standalone/camera_windows.py)**
```powershell
# Test 1: Camera detection
python -m app.standalone.camera_windows

# Expected output:
# - Detects available cameras
# - Tests first camera successfully
# - Captures frames without errors

# Test 2: Multiple cameras (if available)
# Connect USB webcam + use built-in
# Verify both cameras detected

# Test 3: Camera permissions
# Windows Settings → Privacy → Camera
# Disable camera permission
# Run test - verify helpful error message displayed
```

**3. Backend Thread (app/standalone/backend_thread.py)**
```powershell
# Test 1: Basic startup
python -m app.standalone.backend_thread

# Expected output:
# - Backend starts without errors
# - Camera opens successfully
# - CV pipeline runs
# - Database created in %APPDATA%
# - No exceptions for 10+ minutes

# Monitor:
Task Manager:
- Memory usage should be <200 MB
- CPU usage should average <15%

# Test 2: Graceful shutdown
# Press Ctrl+C
# Verify clean shutdown, no orphaned processes

# Test 3: Database inspection
sqlite3 %APPDATA%\DeskPulse\deskpulse.db
.tables  # Should show all tables
PRAGMA journal_mode;  # Should show 'wal'
.quit
```

**4. 30-Minute Continuous Run (Story DoD)**
```powershell
# Run backend for 30 minutes
python -m app.standalone.backend_thread

# Monitor continuously:
- Task Manager (memory, CPU)
- Log file: %APPDATA%\DeskPulse\logs\deskpulse.log
- Watch for exceptions
- Check for memory leaks (memory should stabilize)

# Success criteria:
✅ No exceptions/crashes
✅ Memory stays <200 MB
✅ CPU averages <15%
✅ Posture detection working (check logs)
```

**5. Full Test Suite on Windows**
```powershell
# Run all tests
venv\Scripts\pytest tests\test_standalone_*.py -v

# All 73 tests must pass on Windows
```

---

### Issue #4: Windows-Specific Error Messages (HIGH)

**Location:** Story AC10

Test these error scenarios on Windows:

**1. Camera Permission Denied**
```powershell
# Disable camera in Windows Settings
# Run backend, verify error message shows:
ERROR: Camera access denied by Windows
Windows 10/11 requires explicit camera permission.
Fix: Settings → Privacy → Camera → Allow apps to access camera
```

**2. Antivirus Blocking Database**
```powershell
# Configure Windows Defender to block %APPDATA%\DeskPulse
# Run backend, verify error message shows fix instructions
```

**3. Long Path Issues**
```powershell
# Test with very long username (or nested folder structure)
# Verify detection of >260 char paths
# Verify helpful error message displayed
```

**4. OneDrive Synced AppData (Enterprise)**
```powershell
# If %APPDATA% is OneDrive-synced (corporate environments)
# Verify warning message displayed
# Test database doesn't conflict across devices
```

---

### Issue #5: Performance Validation (HIGH)

**Location:** Task 5

Run performance monitoring test:

```powershell
# Create performance test script
venv\Scripts\python
>>> import psutil, os
>>> from app.standalone.backend_thread import start_backend
>>> from app.standalone.config import load_config, setup_logging
>>>
>>> setup_logging()
>>> config = load_config()
>>> backend = start_backend(config)
>>>
>>> # Monitor for 30 minutes
>>> import time
>>> process = psutil.Process(os.getpid())
>>> for i in range(180):  # 30 min (10-sec intervals)
...     mem_mb = process.memory_info().rss / 1024 / 1024
...     cpu_pct = process.cpu_percent(interval=1)
...     print(f"[{i*10}s] Memory: {mem_mb:.1f}MB, CPU: {cpu_pct:.1f}%")
...     time.sleep(9)
...
>>> backend.stop()
```

**Success Criteria:**
- Memory < 200 MB throughout (no leaks)
- CPU averages < 15% (spikes ok during pose detection)
- No continuous memory growth pattern
- No crashes or exceptions

---

## 📋 TESTING CHECKLIST

Before marking Story 8.1 complete, verify:

### Environment Setup
- [ ] Windows 10 OR Windows 11 hardware/VM available
- [ ] Python 3.11+ installed
- [ ] All dependencies installed successfully
- [ ] Webcam available (built-in or USB)

### Configuration (AC1)
- [ ] Config file created in %APPDATA%/DeskPulse/
- [ ] Database file accessible and writable
- [ ] Log directory created with proper permissions
- [ ] Works with non-ASCII usernames (tested)
- [ ] Config.json is valid JSON (verified)
- [ ] Paths handle spaces correctly

### Backend (AC2)
- [ ] Backend starts successfully without systemd
- [ ] No sdnotify calls or import errors
- [ ] Logging works with file-based handlers
- [ ] Clean shutdown without systemd dependencies

### Flask App (AC3)
- [ ] create_app() accepts standalone_mode parameter
- [ ] SocketIO skipped when standalone_mode=True
- [ ] Talisman skipped when standalone_mode=True
- [ ] Database initializes with custom path
- [ ] App context works in background thread

### Camera (AC5)
- [ ] WindowsCamera opens successfully on Windows
- [ ] CV pipeline uses Windows camera without errors
- [ ] Camera config from config.json applied correctly
- [ ] Fallback to index 0 works if no config
- [ ] Camera errors logged clearly

### Logging (AC6)
- [ ] Logs written to %APPDATA%/DeskPulse/logs/deskpulse.log
- [ ] Log rotation works (create 11+ MB of logs, verify)
- [ ] 5 backup files created correctly
- [ ] Log level configurable from config.json
- [ ] UTF-8 encoding preserves special characters

### Database (AC7)
- [ ] Database file created in %APPDATA%/DeskPulse/
- [ ] WAL mode enabled (check for .db-wal and .db-shm files)
- [ ] Schema matches Pi version
- [ ] Can write/read posture events
- [ ] Database survives simulated crash (kill process, restart)

### Error Handling (AC9 + AC10)
- [ ] Camera permission denied shows helpful message
- [ ] Antivirus blocking shows fix instructions
- [ ] Long path issues detected and logged
- [ ] OneDrive sync warning displayed (if applicable)
- [ ] Import errors handled gracefully

### Performance (Task 5, DoD)
- [ ] Memory usage starts <100 MB
- [ ] Memory usage stays <200 MB after 30-min run
- [ ] No continuous memory growth (leak-free)
- [ ] CPU usage averages <15% during monitoring
- [ ] No crashes in 30-minute continuous test

### Tests (AC12, DoD)
- [ ] All 73 tests pass on Windows
- [ ] Test coverage ≥80% for core modules
- [ ] No test failures specific to Windows

---

## 🚨 KNOWN LIMITATIONS

**Cannot Test on Linux:**
- DirectShow camera backend (Windows-only)
- %APPDATA% path behavior (Windows-only)
- Windows Privacy → Camera permissions (OS feature)
- Antivirus interference (Windows-specific)
- OneDrive-synced folders (Enterprise Windows)

**Why Linux Tests Aren't Enough:**
- OpenCV DirectShow backend behaves differently than V4L2 (Linux)
- Windows file system has different permissions model
- %APPDATA% vs /home paths have different edge cases
- Windows camera permissions prompt doesn't exist on Linux
- Performance characteristics differ (thread scheduling, memory)

---

## ✅ HOW TO MARK STORY COMPLETE

**After completing all Windows testing:**

1. Document results in story file:
```markdown
## Windows Validation Results (2026-01-XX)

**Tested On:**
- Windows 10 22H2 (Build 19045.xxxx)
- Windows 11 23H2 (Build 22631.xxxx)

**Test Results:**
- ✅ All 73 tests pass on Windows
- ✅ 30-minute continuous run: No crashes
- ✅ Memory usage: Max 185 MB (under 200 MB limit)
- ✅ CPU usage: Avg 12% (under 15% limit)
- ✅ Camera detection working on both OS versions
- ✅ Non-ASCII paths tested (José, München usernames)
- ✅ Error messages display correctly
- ✅ WAL mode enabled (verified .db-wal files exist)

**Issues Found:** (list any issues discovered)
**Fixes Applied:** (list any fixes needed)
```

2. Update sprint-status.yaml:
```yaml
  - id: "8.1"
    title: "Windows Backend Port"
    status: done  # Change from ready-for-dev to done
    windows_validated: true
    windows_test_date: "2026-01-XX"
```

3. Update Definition of Done in story:
```markdown
✅ All P0 and P1 tasks completed
✅ Backend starts on Windows 10/11 without errors
✅ WindowsCamera captures frames successfully
✅ Database created in %APPDATA%/DeskPulse/ with WAL mode enabled
✅ Logs written to %APPDATA%/DeskPulse/logs/deskpulse.log
✅ All unit tests pass with 80%+ code coverage
✅ No Python exceptions in 30-minute continuous test run
✅ Memory usage <200 MB, CPU usage <15% average
✅ Code validated on actual Windows 10 AND Windows 11  ← MARK THIS
```

---

## 📞 CONTACT

**Questions about Windows testing?**
Refer to: `/docs/WINDOWS-STANDALONE-SETUP.md`

**Found issues during Windows testing?**
Document in story file under "Windows Validation Results"

**Cannot access Windows hardware?**
- Use free Windows 10/11 development VM (90-day license)
- GitHub Actions Windows runner (for CI/CD)
- Rent cloud Windows instance (AWS, Azure, GCP)

---

**Last Updated:** 2026-01-07 (After automated code review fixes)
**Next Update:** After Windows validation testing complete
