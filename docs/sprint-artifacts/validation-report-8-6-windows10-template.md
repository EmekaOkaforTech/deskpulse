# Story 8.6 Validation Report - Windows 10

**Story**: 8.6 All-in-One Installer for Windows Standalone Edition
**Test Date**: YYYY-MM-DD
**Tester**: [Name]
**Environment**: Clean Windows 10 VM (no Python, no dev tools)

---

## Test Environment

### Hardware/VM Specifications
- **OS Version**: Windows 10 Build _____ (e.g., 22H2 Build 19045)
- **Architecture**: 64-bit
- **RAM**: ___ GB
- **CPU**: ___
- **Webcam**: [ ] Built-in  [ ] USB  [ ] None  (Model: ___)
- **VM Software**: [ ] Hyper-V  [ ] VirtualBox  [ ] VMware  [ ] Physical Hardware

### Clean State Verification
```powershell
# Run these commands to verify clean state:
python --version       # Should fail: "python is not recognized"
pip --version          # Should fail
where python           # Should return: "INFO: Could not find files"
```

**Clean state verified**: [ ] YES  [ ] NO (if NO, stop and reset VM)

### Test Artifacts
- **Installer**: `DeskPulse-Standalone-Setup-v2.0.0.exe`
- **Installer Size**: ___ MB (expected: 150-250 MB)
- **SHA256 Checksum**: `________________________________`
- **Download Source**: [ ] GitHub Release  [ ] Local build  [ ] Network share

---

## Test 1: Installation

### Installation Process
**Start Time**: ___:___
**End Time**: ___:___
**Duration**: ___ seconds

**Installation Steps**:
- [ ] Installer launches successfully
- [ ] SmartScreen warning appears (expected)
  - [ ] "More info" button visible
  - [ ] "Run anyway" button appears after clicking "More info"
  - [ ] Installation proceeds after "Run anyway"
- [ ] Modern installation wizard displays
- [ ] License agreement shown (if applicable)
- [ ] Installation directory shown: `C:\Program Files\DeskPulse`
- [ ] Auto-start checkbox visible: "Start DeskPulse automatically when Windows starts"
- [ ] Auto-start checkbox UNCHECKED by default
- [ ] Installation progress bar displays
- [ ] Post-install launch checkbox visible: "Launch DeskPulse"
- [ ] Installation completes without errors

**Test Auto-Start Checkbox**:
- [ ] Checked "Start automatically" during install
- [ ] Installation completed
- [ ] Shortcut created: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DeskPulse.lnk`

**Installation Result**: [ ] PASS  [ ] FAIL

**Issues Found**:
```
(If FAIL, describe issues here)
```

---

## Test 2: First Launch

### Application Startup
**Start Time**: ___:___
**Tray Icon Appeared**: ___:___
**Startup Duration**: ___ seconds (target: <5 seconds)

**Startup Verification**:
- [ ] Application launches (no errors)
- [ ] No console window appears
- [ ] System tray icon appears (teal color - monitoring)
- [ ] No error dialogs appear
- [ ] Startup time within target (<5 seconds)

**User Data Creation**:
- [ ] `%APPDATA%\DeskPulse\` directory created
- [ ] `config.json` created
- [ ] `deskpulse.db` created (SQLite database)
- [ ] `logs\deskpulse.log` created

**Verify User Data**:
```powershell
# Check files created
dir %APPDATA%\DeskPulse
type %APPDATA%\DeskPulse\config.json
dir %APPDATA%\DeskPulse\logs
```

**First Launch Result**: [ ] PASS  [ ] FAIL

**Issues Found**:
```
(If FAIL, describe issues and check logs at %APPDATA%\DeskPulse\logs\deskpulse.log)
```

---

## Test 3: Functional Validation

### Tray Icon and Menu
**Right-click tray icon**:
- [ ] Menu appears correctly
- [ ] "Pause Monitoring" option visible
- [ ] "Resume Monitoring" option visible (grayed out initially)
- [ ] "Today's Stats" submenu visible
- [ ] "Settings" option visible
- [ ] "About DeskPulse" option visible
- [ ] "Quit DeskPulse" option visible

### Pause/Resume Functionality
- [ ] Click "Pause Monitoring"
  - [ ] Tray icon changes to gray
  - [ ] "Pause Monitoring" becomes grayed out
  - [ ] "Resume Monitoring" becomes active
- [ ] Click "Resume Monitoring"
  - [ ] Tray icon changes back to teal
  - [ ] "Resume Monitoring" becomes grayed out
  - [ ] "Pause Monitoring" becomes active

### Stats Display
- [ ] Click "Today's Stats" → "Posture Summary"
  - [ ] MessageBox appears
  - [ ] Displays posture statistics
  - [ ] Data format correct (time, percentages, etc.)

### Settings Display
- [ ] Click "Settings" → "Open Config File"
  - [ ] MessageBox shows config path: `%APPDATA%\DeskPulse\config.json`
  - [ ] Path is correct

### About Dialog
- [ ] Click "About DeskPulse"
  - [ ] MessageBox appears
  - [ ] Shows version: **2.0.0**
  - [ ] Shows platform info (Windows 10, Python version, etc.)
  - [ ] Shows GitHub link
  - [ ] All information accurate

### Quit Functionality
- [ ] Click "Quit DeskPulse"
  - [ ] Confirmation dialog appears: "Are you sure you want to quit DeskPulse?"
  - [ ] Click "Yes"
  - [ ] Application exits cleanly
  - [ ] Tray icon disappears
  - [ ] Process terminates (check Task Manager)

**Functional Test Result**: [ ] PASS  [ ] FAIL

**Issues Found**:
```
(If FAIL, describe issues)
```

---

## Test 4: Camera Integration

### Camera Detection
- [ ] Webcam connected (built-in or USB)
- [ ] Camera LED turns on (indicates capture active)
- [ ] Check logs for camera detection:
  ```
  [timestamp] INFO: Camera detected: index=0
  [timestamp] INFO: Camera initialized: DirectShow backend
  ```

**Camera Detection Result**: [ ] PASS  [ ] FAIL  [ ] N/A (no camera)

### Pose Detection
- [ ] Sit with good posture (upright)
  - [ ] Tray icon remains teal (monitoring)
  - [ ] No alerts triggered
- [ ] Slouch (bad posture)
  - [ ] Toast notification appears after threshold
  - [ ] Tray icon may change to orange/red (alert state)
  - [ ] Notification displays "Poor posture detected"

**Pose Detection Result**: [ ] PASS  [ ] FAIL  [ ] N/A (no camera)

### Camera Error Handling (if no camera)
- [ ] Disconnect camera (or test with no camera)
- [ ] Tray icon shows disconnected state
- [ ] Logs show graceful degradation: "Camera not available, monitoring disabled"
- [ ] Application remains functional (UI still works)

**Error Handling Result**: [ ] PASS  [ ] FAIL  [ ] N/A (camera available)

---

## Test 5: Performance Metrics

### Startup Performance
- **Cold start time**: ___ seconds (target: <5 seconds)
- **Warm start time**: ___ seconds (second launch)
- **Result**: [ ] PASS (<5s)  [ ] FAIL (≥5s)

### Memory Usage
**Measurement Method**: Task Manager → Details → DeskPulse.exe → Memory (Private Working Set)

- **At startup**: ___ MB
- **After 5 minutes**: ___ MB (target: <255 MB)
- **After 30 minutes**: ___ MB (target: <255 MB)
- **Memory growth**: ___% over 30 minutes (target: <10%)

**Memory Test Result**: [ ] PASS (<255 MB)  [ ] FAIL (≥255 MB)

### CPU Usage
**Measurement Method**: Task Manager → Performance tab or Resource Monitor

- **Idle (monitoring paused)**: ___% (target: <10%)
- **Monitoring active (good posture)**: ___% (target: <35%)
- **Monitoring active (pose detection)**: ___% (target: <35%)

**CPU Test Result**: [ ] PASS (<35% avg)  [ ] FAIL (≥35%)

### Disk I/O
- **Database writes**: Check logs for excessive I/O warnings
- **Log file size**: ___ KB (after 30 minutes)
- **Result**: [ ] PASS (reasonable)  [ ] FAIL (excessive)

---

## Test 6: 30-Minute Stability Test

### Test Setup
- **Start Time**: ___:___
- **End Time**: ___:___
- **Duration**: 30 minutes
- **Monitoring State**: [ ] Active  [ ] Paused

### Stability Metrics
- **Application Crashes**: ___ (target: 0)
- **Unhandled Exceptions**: ___ (check logs)
- **Memory Leaks**: [ ] None detected  [ ] Detected (describe)
- **Camera Disconnections**: ___ (unexpected)
- **Backend Errors**: ___ (check logs)

### Final Measurements (30-minute mark)
- **Memory**: ___ MB
- **CPU (avg)**: ___%
- **Log file size**: ___ KB
- **Database size**: ___ KB
- **Posture events recorded**: ___ (if monitoring active)

**Stability Test Result**: [ ] PASS (0 crashes)  [ ] FAIL (≥1 crash)

**Issues Found**:
```
(If FAIL, describe issues and attach relevant logs)
```

---

## Test 7: Auto-Start Validation

### Reboot Test
**Prerequisites**: Installer run with "Start automatically" checked

- [ ] Reboot Windows VM
- [ ] Login to user account
- [ ] Wait 30 seconds after desktop appears
- [ ] Tray icon appears automatically (within 10 seconds of desktop ready)
- [ ] Application starts without errors
- [ ] Single instance check works (no duplicate processes in Task Manager)
- [ ] Auto-start time: ___ seconds (from desktop to tray icon)

**Auto-Start Result**: [ ] PASS  [ ] FAIL  [ ] N/A (not tested)

**Issues Found**:
```
(If FAIL, describe issues)
```

---

## Test 8: Uninstaller

### Uninstall Process
- [ ] Open Control Panel → Programs and Features
- [ ] Find "DeskPulse Standalone Edition"
- [ ] Click "Uninstall"
- [ ] Uninstaller starts

### User Data Preservation Prompt
- [ ] Dialog appears: "Do you want to delete your configuration, database, and logs?"
- [ ] Dialog shows location: `%APPDATA%\DeskPulse`
- [ ] Dialog lists: config.json, deskpulse.db, logs/
- [ ] "If you plan to reinstall..." message visible

### Test "No" (Preserve Data)
- [ ] Click "No"
- [ ] Uninstaller completes
- [ ] Program Files directory removed: `C:\Program Files\DeskPulse\`
- [ ] Start Menu shortcuts removed
- [ ] Auto-start shortcut removed (if enabled)
- [ ] User data PRESERVED:
  - [ ] `%APPDATA%\DeskPulse\config.json` exists
  - [ ] `%APPDATA%\DeskPulse\deskpulse.db` exists
  - [ ] `%APPDATA%\DeskPulse\logs\` exists
- [ ] Confirmation message: "Configuration and logs preserved"

### Test "Yes" (Delete Data)
**Reinstall first, then uninstall again**:
- [ ] Reinstall DeskPulse
- [ ] Run uninstaller again
- [ ] Click "Yes" to delete data
- [ ] Uninstaller completes
- [ ] User data DELETED: `%APPDATA%\DeskPulse\` directory removed
- [ ] Confirmation message: "Configuration, database, and logs deleted successfully"

**Uninstaller Result**: [ ] PASS  [ ] FAIL

**Issues Found**:
```
(If FAIL, describe issues)
```

---

## Test 9: Backend Bundling Verification

### Check Backend DLLs Bundled
**Location**: `C:\Program Files\DeskPulse\_internal\`

```powershell
# Verify backend components exist
dir "C:\Program Files\DeskPulse\_internal\cv2"
dir "C:\Program Files\DeskPulse\_internal\mediapipe"
dir "C:\Program Files\DeskPulse\_internal\flask"
```

**Backend Components**:
- [ ] cv2 (OpenCV) directory exists
- [ ] mediapipe directory exists
- [ ] flask directory exists
- [ ] numpy directory exists
- [ ] sqlite3 module bundled

**Backend Bundling Result**: [ ] PASS  [ ] FAIL

---

## Test 10: Error Handling

### Configuration Corruption
- [ ] Close DeskPulse
- [ ] Corrupt config.json (add invalid JSON syntax)
- [ ] Launch DeskPulse
- [ ] Application starts with default config
- [ ] Warning logged: "Failed to load config, using defaults"
- [ ] Application functional

**Config Error Handling**: [ ] PASS  [ ] FAIL

### Disk Full Simulation
- [ ] (Optional) Fill disk to <100 MB free
- [ ] Launch DeskPulse
- [ ] Verify graceful degradation (logs error, continues)

**Disk Full Handling**: [ ] PASS  [ ] FAIL  [ ] N/A (not tested)

### Second Instance Launch
- [ ] Launch DeskPulse (first instance running)
- [ ] Try to launch DeskPulse.exe again
- [ ] MessageBox appears: "DeskPulse is already running"
- [ ] Second instance exits
- [ ] First instance continues running

**Single Instance Check**: [ ] PASS  [ ] FAIL

---

## Summary

### Overall Test Results
- **Installation**: [ ] PASS  [ ] FAIL
- **First Launch**: [ ] PASS  [ ] FAIL
- **Functionality**: [ ] PASS  [ ] FAIL
- **Camera Integration**: [ ] PASS  [ ] FAIL  [ ] N/A
- **Performance**: [ ] PASS  [ ] FAIL
- **Stability (30 min)**: [ ] PASS  [ ] FAIL
- **Auto-Start**: [ ] PASS  [ ] FAIL  [ ] N/A
- **Uninstaller**: [ ] PASS  [ ] FAIL
- **Backend Bundling**: [ ] PASS  [ ] FAIL
- **Error Handling**: [ ] PASS  [ ] FAIL

### Final Verdict
**Windows 10 Validation**: [ ] PASS (all tests passed)  [ ] FAIL (1+ tests failed)

### Performance Summary
| Metric | Measured | Target | Status |
|--------|----------|--------|--------|
| Installer Size | ___ MB | 150-250 MB | [ ] PASS  [ ] FAIL |
| Startup Time | ___ s | <5s | [ ] PASS  [ ] FAIL |
| Memory (30 min) | ___ MB | <255 MB | [ ] PASS  [ ] FAIL |
| CPU (avg) | ___% | <35% | [ ] PASS  [ ] FAIL |
| Crashes (30 min) | ___ | 0 | [ ] PASS  [ ] FAIL |

### Critical Issues Found
```
(List any blocking issues that prevent release)
1.
2.
```

### Minor Issues Found
```
(List non-blocking issues for future improvement)
1.
2.
```

### Recommendations
```
(Recommendations for release decision)
-
-
```

---

## Log Excerpts

### Startup Logs
```
(Paste first 50 lines of %APPDATA%\DeskPulse\logs\deskpulse.log)
```

### Error Logs (if any)
```
(Paste any ERROR or CRITICAL log entries)
```

---

## Attachments

- [ ] Full log file: `deskpulse.log` (attached)
- [ ] Screenshots: Tray icon, menu, about dialog, notifications
- [ ] Task Manager screenshot: Memory and CPU usage
- [ ] %APPDATA%\DeskPulse directory structure

---

**Validation Completed By**: [Name]
**Date**: YYYY-MM-DD
**Signature**: ________________
