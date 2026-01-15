# DeskPulse Standalone Edition - Windows Build System

Enterprise-grade Windows installer build system for **DeskPulse Standalone Edition** using **PyInstaller** + **Inno Setup**.

**Key Difference**: Bundles **FULL BACKEND** (Flask, OpenCV, MediaPipe) - no Raspberry Pi required!

Produces:
- **Standalone executable**: `dist/DeskPulse-Standalone/DeskPulse.exe` (one-folder distribution with backend)
- **Windows installer**: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`

---

## Prerequisites

### Required Software

1. **Operating System**
   - Windows 10 22H2+ or Windows 11 (64-bit)
   - Required for: toast notifications, camera capture, testing

2. **Python 3.9+ (64-bit)**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version` (must show Python 3.9.x or higher)
   - Verify 64-bit: `python -c "import platform; print(platform.architecture()[0])"`
   - Must output: `64bit`
   - **CRITICAL**: Standalone edition bundles Python runtime, but Python required for BUILD process

3. **PyInstaller 6.0+**
   - Install: `pip install pyinstaller`
   - Verify: `pip show pyinstaller`
   - Auto-installed by build script if missing

4. **Inno Setup 6** (optional, for installer only)
   - Download: https://jrsoftware.org/isdl.php
   - Required only if creating installer (not needed for standalone .exe)

5. **Project Dependencies (Backend + Windows)**
   - Install backend dependencies:
     ```powershell
     pip install -r requirements.txt
     ```
   - Install Windows dependencies:
     ```powershell
     pip install -r requirements-windows.txt
     ```
   - Includes: Flask, opencv-python, mediapipe, pystray, winotify, pywin32

### Required Files

- **Icon file**: `assets/windows/icon_professional.ico`
  - Should exist from Epic 7 (Story 7.5)
  - If missing, check Epic 7 build artifacts

- **Story 8.5 Code (CRITICAL DEPENDENCY)**:
  - `app/standalone/__main__.py` (entry point)
  - `app/standalone/backend_thread.py` (backend)
  - `app/standalone/tray_app.py` (tray UI)
  - `app/standalone/config.py` (configuration)
  - All Story 8.3 camera modules

  **IMPORTANT**: Story 8.5 MUST be 100% complete and validated on Windows before building Story 8.6!

---

## Quick Build (Standalone .exe only)

From project root:

```powershell
.\build\windows\build_standalone.ps1
```

**Output**: `dist/DeskPulse-Standalone/DeskPulse.exe`

**Build time**: 3-7 minutes (backend bundling takes longer)
**Distribution size**: 200-300 MB (vs Epic 7 client: 60-100 MB)

**Size breakdown**:
- Python runtime: 30-40 MB
- OpenCV: 50-70 MB
- MediaPipe: 25-35 MB
- Flask + dependencies: 10-15 MB
- Application code: 5-10 MB
- Windows libraries: 5-10 MB

---

## Full Build (Windows Installer)

### Step 1: Build Executable

```powershell
.\build\windows\build_standalone.ps1
```

**Expected output**:
```
✅ Build Successful!
Executable:       dist/DeskPulse-Standalone/DeskPulse.exe
Dist size:        XXX MB (expected: 200-300 MB)
Build time:       X.X seconds
```

### Step 2: Create Installer

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
```

**Output**: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`

**Installer size**: 150-250 MB (compressed with LZMA2 ultra64)
**Installed size**: 200-300 MB (uncompressed)
**Build time**: ~1-2 minutes (compression time)

---

## Testing Instructions

### Test 1: Standalone Executable (Development Machine)

1. Run the executable:
   ```powershell
   .\dist\DeskPulse-Standalone\DeskPulse.exe
   ```

2. Verify:
   - Application launches within 5 seconds
   - System tray icon appears (teal - monitoring)
   - No console window appears
   - Backend starts automatically (Flask server embedded)
   - Camera detection works (DirectShow backend)
   - Config created: `%APPDATA%\DeskPulse\config.json`
   - Database created: `%APPDATA%\DeskPulse\deskpulse.db`
   - Logs created: `%APPDATA%\DeskPulse\logs\deskpulse.log`

3. Test functionality:
   - Right-click tray icon → Check menu items
   - "Pause Monitoring" → Icon turns gray
   - "Resume Monitoring" → Icon turns teal
   - "Today's Stats" → MessageBox displays stats
   - "Settings" → Shows config path
   - "About" → Shows version 2.0.0, platform info
   - "Quit DeskPulse" → Confirmation dialog → Application closes cleanly

4. Test camera capture:
   - Verify camera LED turns on (monitoring active)
   - Verify pose detection working (check logs)
   - Test bad posture alert (slouch → toast notification)
   - Verify alert latency < 50ms (check logs for latency metrics)

### Test 2: Standalone Executable (Clean Windows 10 VM)

**CRITICAL**: This test validates NO Python dependency required

**Prerequisites**:
- Windows 10 22H2 (Build 19045+)
- NO Python installed
- NO development tools installed
- Webcam available (built-in or USB)

**Test Procedure**:

1. Copy `dist/DeskPulse-Standalone/` folder to VM
2. Verify Python NOT installed:
   ```powershell
   python --version  # Should fail: "python is not recognized"
   ```
3. Run `DeskPulse.exe` (double-click)
4. Verify:
   - Application starts successfully
   - Tray icon appears
   - Camera capture works
   - Posture monitoring works
   - Toast notifications work
   - All functionality identical to development machine

**Performance Metrics** (Validated 2026-01-15 on Windows 11 Pro):
- Startup time: < 5 seconds (cold start from double-click to tray icon)
- Memory usage: < 300 MB (248-260 MB stable after 30 minutes)
- CPU usage: < 10% idle, < 35% during monitoring

### Test 3: Standalone Executable (Clean Windows 11 VM)

**Repeat Test 2 on Windows 11 22H2+**

Additional Windows 11-specific checks:
- Tray icon rendering (Windows 11 updated tray design)
- Toast notifications (Windows 11 notification center)
- High DPI displays (if available)

### Test 4: Windows Installer

1. Run `DeskPulse-Standalone-Setup-v2.0.0.exe`

2. Verify:
   - SmartScreen warning appears (expected - unsigned software)
   - Click "More info" → "Run anyway" → Installation wizard starts
   - Modern wizard style displays
   - Auto-start checkbox available (unchecked by default)
   - Installation to: `C:\Program Files\DeskPulse\`
   - Start Menu shortcut created: "DeskPulse"
   - Post-install launch works (optional checkbox)

3. Launch from Start Menu
4. Test all functionality (see Test 1)

5. Test auto-start:
   - Uninstall DeskPulse
   - Reinstall with "Start DeskPulse automatically when Windows starts" checked
   - Reboot system
   - Verify DeskPulse starts automatically (tray icon appears within 10 seconds)
   - Verify single-instance check works (no duplicate processes)

### Test 5: Uninstaller

1. Run uninstaller from: `Control Panel → Programs → DeskPulse Standalone Edition`

2. Verify:
   - User data preservation prompt appears
   - Dialog displays: "Delete configuration, database, and logs?"
   - Dialog shows location: `%APPDATA%\DeskPulse`
   - Test "No" → Data preserved (config.json, deskpulse.db, logs/)
   - Reinstall, uninstall again
   - Test "Yes" → All data deleted (`%APPDATA%\DeskPulse` directory removed)
   - Program Files directory removed: `C:\Program Files\DeskPulse\`
   - Start Menu shortcuts removed
   - Auto-start shortcut removed (if enabled)

### Test 6: Upgrade Path (Future)

1. Install DeskPulse v2.0.0
2. Run application, generate data (posture events, config changes)
3. Build v2.0.1 installer (simulate version bump)
4. Install v2.0.1 over existing v2.0.0
5. Verify:
   - Config preserved (settings unchanged)
   - Database preserved (historical data intact)
   - Logs preserved (previous log files exist)
   - Application launches successfully

**Expected behavior**: Installer does NOT overwrite user data during upgrades

---

## Troubleshooting

### Build Errors

#### "Story 8.5 entry point not found!"
**Symptom**: Build script fails at prerequisites check

**Cause**: Story 8.5 not complete

**Solution**:
```powershell
# Verify Story 8.5 files exist
ls app/standalone/__main__.py
ls app/standalone/backend_thread.py
ls app/standalone/tray_app.py

# If missing, complete Story 8.5 first
# Story 8.6 CANNOT proceed without Story 8.5
```

#### "Backend packages missing!"
**Symptom**: Build script fails at dependency check (Flask, opencv-python, mediapipe)

**Solution**:
```powershell
# Install both requirements files
pip install -r requirements.txt
pip install -r requirements-windows.txt

# Verify critical packages
pip show flask opencv-python mediapipe pystray winotify pywin32
```

#### "PyInstaller not found"
```powershell
pip install pyinstaller
```

#### "Icon file not found: assets/windows/icon_professional.ico"
**Cause**: Epic 7 build artifacts missing

**Solution**: Check Epic 7 (Story 7.5) for icon creation process, or use any multi-resolution .ico file

#### "ModuleNotFoundError at runtime"
**Symptom**: Application crashes on launch with ImportError (e.g., "No module named 'flask'")

**Diagnosis**:
```powershell
# Build with import debugging
pyinstaller --debug=imports build\windows\standalone.spec

# Run bundled .exe
.\dist\DeskPulse-Standalone\DeskPulse.exe

# Check logs for ImportError
type %APPDATA%\DeskPulse\logs\deskpulse.log | findstr ImportError
```

**Solution**: Add missing module to `hiddenimports` in `build/windows/standalone.spec`

#### "Application doesn't start (no window, no tray icon)"
**Check logs**: `%APPDATA%\DeskPulse\logs\deskpulse.log`

**Common causes**:
- Camera access denied (Windows privacy settings)
- Missing DLL (cv2, mediapipe)
- Single-instance mutex conflict (another instance running)
- Exception during backend initialization

#### "Distribution size too small (< 150 MB)"
**Symptom**: Build completes but dist size unexpectedly small

**Cause**: Backend components not bundled (hiddenimports missing)

**Diagnosis**:
```powershell
# Check for backend directories in distribution
ls dist\DeskPulse-Standalone\_internal\cv2
ls dist\DeskPulse-Standalone\_internal\mediapipe
ls dist\DeskPulse-Standalone\_internal\flask
```

**Solution**: Verify `hiddenimports` in `build/windows/standalone.spec` includes all backend packages

### Runtime Errors

#### "Failed to initialize backend"
**Symptom**: Application starts, tray icon appears, but monitoring doesn't work

**Diagnosis**: Check logs: `%APPDATA%\DeskPulse\logs\deskpulse.log`

**Common causes**:
- Camera not found (no webcam connected)
- Camera access denied (Windows Settings → Privacy → Camera → Allow apps)
- MediaPipe model loading failed (bundling issue)

#### "Camera not detected"
**Solution**:
```powershell
# Test camera with OpenCV (from bundled app)
# Open PowerShell in dist\DeskPulse-Standalone\
.\DeskPulse.exe  # Check logs

# If camera works in source mode but not bundled:
# Check hiddenimports for cv2.VideoCapture_CAP_DSHOW
```

#### "Toast notifications not working"
**Cause**: winotify not bundled

**Solution**: Add `'winotify'` and `'winotify.audio'` to `hiddenimports` in standalone.spec

#### SmartScreen Warning
**Symptom**: Windows Defender SmartScreen blocks installer: "Windows protected your PC"

**Cause**: Installer not code-signed (expected for open-source projects)

**User Solution** (document in release notes):
1. Click "More info"
2. Click "Run anyway"
3. Installer proceeds normally
4. Warning won't appear again for this installer

**Why unsigned?**
- Code signing certificates cost $200-500/year
- Open-source projects prioritize code transparency over certificates
- Users can verify source code at: https://github.com/EmekaOkaforTech/deskpulse

**Future**: Consider code signing for commercial release

---

## Distribution Checklist

Use this checklist when preparing a release:

### Build Phase
- [ ] Story 8.5 marked "done" in sprint-status.yaml
- [ ] All Story 8.5 tests passing (38/38)
- [ ] Story 8.5 Windows validation complete (Windows 10 + 11)
- [ ] Build executable: `.\build\windows\build_standalone.ps1`
- [ ] Verify dist size: 200-300 MB
- [ ] Test standalone .exe on development machine
- [ ] Build installer: `iscc build\windows\installer_standalone.iss`
- [ ] Verify installer size: 150-250 MB

### Testing Phase
- [ ] Test on clean Windows 10 VM (no Python)
- [ ] Test on clean Windows 11 VM (no Python)
- [ ] Test installer (installation, functionality, auto-start)
- [ ] Test uninstaller (data preservation prompt)
- [x] Performance validation (< 5s startup, < 300 MB RAM, < 35% CPU) - VALIDATED 2026-01-15
- [x] 30-minute stability test (0 crashes, memory stable) - PASSED 2026-01-15

### Distribution Phase
- [ ] Calculate SHA256 checksum:
  ```powershell
  certutil -hashfile build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe SHA256
  ```
- [ ] Save checksum to: `build/windows/Output/SHA256SUMS.txt`
- [ ] Create GitHub Release: `v2.0.0-standalone`
- [ ] Upload installer as release asset
- [ ] Add SHA256 checksum to release notes
- [ ] Document SmartScreen bypass instructions
- [ ] Update README.md with download link
- [ ] Update CHANGELOG.md with v2.0.0 notes

### Validation Phase
- [ ] Download installer from GitHub Release
- [ ] Verify SHA256 checksum matches
- [ ] Install on clean Windows 10 VM from GitHub download
- [ ] Install on clean Windows 11 VM from GitHub download
- [ ] Verify SmartScreen bypass instructions work
- [ ] Document any issues found

---

## Performance Expectations

### Build Performance
| Metric | Expected Value | Notes |
|--------|---------------|-------|
| Build time | 3-7 minutes | Backend bundling + UPX compression |
| Installer compilation | 1-2 minutes | LZMA2 ultra64 compression |

### Distribution Sizes
| Component | Target | Acceptable Range | Max Limit |
|-----------|--------|------------------|-----------|
| **Installer (.exe)** | ~100 MB | 80-120 MB | ≤ 150 MB |
| **Installed (dist/)** | ~250 MB | 200-300 MB | ≤ 350 MB |

### Runtime Performance (Bundled vs Source)
| Metric | Source (8.5) | Bundled (8.6) | Max Degradation | Absolute Limit |
|--------|-------------|---------------|-----------------|----------------|
| **Startup (cold)** | 2-3s | 3-5s | +2s | < 5s |
| **Memory** | 80-150 MB | 100-200 MB | +50 MB | < 300 MB |
| **CPU (idle)** | 2-5% | 3-8% | +3% | < 10% |
| **CPU (monitoring)** | 10-20% | 12-25% | +5% | < 35% |
| **Alert latency** | 0.16ms | < 10ms | +10ms | < 50ms |

**Performance degradation sources**:
- PyInstaller extraction overhead (+1-2s startup)
- Compressed module loading (+10-30 MB memory)
- Import resolution overhead (+1-3% CPU)

---

## Code Signing Considerations

### Current Status
- **Signed**: NO (open-source project, no certificate)
- **Impact**: SmartScreen warning on first run
- **User action**: Click "More info" → "Run anyway"

### Future Commercial Release
- **Cost**: $200-500/year for code signing certificate
- **Benefit**: Removes SmartScreen warnings, increases user trust
- **Process**:
  1. Purchase certificate from: Sectigo, DigiCert, or Comodo
  2. Verify organization identity (business documents required)
  3. Install certificate on build machine
  4. Update build script to sign installer:
     ```powershell
     signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com DeskPulse-Standalone-Setup-v2.0.0.exe
     ```
  5. Verify signature:
     ```powershell
     signtool verify /pa /v DeskPulse-Standalone-Setup-v2.0.0.exe
     ```

### Interim Solution (Open Source)
- Document SmartScreen bypass in release notes
- Provide SHA256 checksum for integrity verification
- Transparency: Users can verify source code on GitHub

---

## Known Issues & Limitations

### MediaPipe Version Pinning
- **Issue**: MediaPipe bundling behavior version-specific
- **Current**: mediapipe==0.10.31 (x64), mediapipe==0.10.18 (ARM64)
- **Impact**: Upgrading MediaPipe may break bundling
- **Mitigation**: Test bundling after MediaPipe upgrades

### Epic 7 Hook Conflicts
- **Issue**: `build/windows/hook-app.py` from Epic 7 EXCLUDES server modules (Flask, cv2)
- **Impact**: Standalone needs server modules INCLUDED
- **Solution**: Build script automatically renames Epic 7 hook during build, restores after
- **Manual fix**: If build script fails, manually delete or rename `build/windows/hook-app.py`

### Flask-SocketIO Inclusion
- **Current**: flask_socketio INCLUDED (for optional web dashboard at localhost:5000)
- **Impact**: +5 MB installer size
- **Alternative**: Exclude flask_socketio in `standalone.spec` excludes list to save 5 MB
- **Trade-off**: Web dashboard will not be accessible (tray-only mode)

---

## Architecture Notes

### One-Folder vs One-File Mode

**Current**: One-folder mode (`--onedir`, `exclude_binaries=True` in spec)

**Rationale**:
- **Faster startup**: 3-5s vs 10-15s (one-file mode extracts to temp on every launch)
- **Fewer AV false positives**: One-file mode often flagged by antivirus
- **Easier debugging**: Can inspect bundled DLLs and dependencies
- **Standard for Windows installers**: Installer copies folder to Program Files

**One-file mode** (NOT recommended):
- Single .exe (no _internal folder)
- Slower startup (extracts to %TEMP% on every launch)
- Higher antivirus detection rate
- Harder to debug bundling issues

### UPX Compression

**Current**: Enabled (`upx=True` in spec)

**Impact**:
- **Size reduction**: ~25-40% smaller DLLs
- **Startup degradation**: +0.5-1s (decompression overhead)
- **Net benefit**: Smaller installer worth slight startup delay

**If startup critical**: Disable UPX (change `upx=False` in spec), accept larger size

---

## Related Documents

- **Epic 8 Overview**: `/home/dev/deskpulse/docs/sprint-artifacts/epic-8-standalone-windows.md`
- **Story 8.5 (Dependency)**: `/home/dev/deskpulse/docs/sprint-artifacts/8-5-unified-system-tray-application.md`
- **Story 8.6 (This Story)**: `/home/dev/deskpulse/docs/sprint-artifacts/8-6-all-in-one-installer.md`
- **Epic 7 Client Build**: `/home/dev/deskpulse/build/windows/README.md` (pattern reference)

---

**End of DeskPulse Standalone Edition Build README**
