# Story 8.6: All-in-One Installer for Windows Standalone Edition

---

## ✅ **READY FOR IMPLEMENTATION - Story 8.5 Complete**

**Status:** UNBLOCKED - Story 8.5 validation complete

**Story 8.5 Completion Confirmed:**
- ✅ Story 8.5 status = "done" in sprint-status.yaml
- ✅ Windows 10/11 validation passed (30-minute stability test, 0 crashes)
- ✅ All Story 8.5 tests passing (38/38 unit + integration tests)
- ✅ Performance baseline validated (memory <255 MB, CPU <35%, latency <50ms)
- ✅ All Story 8.5 deliverables committed to git

**Story 8.5 Code Ready for Bundling:**
- `app/standalone/__main__.py` (477 lines) - stable and validated
- `app/standalone/tray_app.py` (643 lines) - Windows tested
- `app/standalone/backend_thread.py` (825 lines) - production-ready
- All components validated on actual Windows 10/11 hardware

**Ready Date:** 2026-01-11

---

Status: ready-for-dev
Validated: 2026-01-11 (SM Agent - 10 improvements applied, ready for implementation after Story 8.5 completes)

## Story

As a Windows user,
I want a professional one-click installer for DeskPulse Standalone Edition,
So that I can install and run the complete posture monitoring application without Python, dependencies, or manual configuration.

---

## **🎯 Definition of Done**

**All of these must be TRUE before marking story complete:**

✅ PyInstaller spec file created: `build/windows/standalone.spec`
✅ Build automation script created: `build/windows/build_standalone.ps1` or `.bat`
✅ Inno Setup installer script created: `build/windows/installer_standalone.iss`
✅ Standalone executable builds successfully: `dist/DeskPulse-Standalone/DeskPulse.exe`
✅ Windows installer creates: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
✅ All backend dependencies bundled (Flask, OpenCV, MediaPipe, SQLite)
✅ All Story 8.5 components included (__main__.py, backend_thread.py, tray_app.py)
✅ Application starts on clean Windows 10/11 (no Python required)
✅ Auto-start option works (Registry/Startup folder)
✅ Clean uninstaller with user data preservation prompt
✅ Professional icon and branding (reuses icon_professional.ico)
✅ Installer size documented (expected: 150-250 MB with full backend)
✅ Startup performance meets target (<5 seconds cold start)
✅ Memory footprint within target (<255 MB after startup)
✅ SmartScreen bypass instructions documented
✅ Build documentation (README) comprehensive and tested
✅ Distribution checklist complete (SHA256, GitHub Release, changelog)

**Story is NOT done if:**

❌ Executable crashes on launch (ImportError, DLL not found)
❌ Backend components missing (Flask, OpenCV, or MediaPipe not bundled)
❌ Camera capture not working (cv2.VideoCapture fails)
❌ Toast notifications not working (winotify not bundled)
❌ Tray icon not appearing (pystray or icon assets missing)
❌ Configuration not persisting (%APPDATA%/DeskPulse not created)
❌ Installer doesn't work on clean Windows VM
❌ Auto-start not working after reboot
❌ Uninstaller leaves orphaned registry keys or files
❌ Any enterprise-grade requirement violated

---

## **📋 Implementation Prerequisites**

**CRITICAL: Story 8.5 MUST be complete before starting Story 8.6.**

### **Story 8.5 Deliverables (Dependencies)**

**1. Main Entry Point:**
```
app/standalone/__main__.py (477 lines)
```
**Status:** ✅ Complete (Story 8.5)
**Features:**
- Single-instance check (Windows mutex)
- Configuration loading (%APPDATA%)
- Event queue creation (PriorityQueue)
- Backend thread initialization
- Callback registration (IPC glue)
- Tray app initialization
- Graceful shutdown sequence
- Exception handling with MessageBox

**2. Tray Application:**
```
app/standalone/tray_app.py (643 lines)
```
**Status:** ✅ Complete (Story 8.5)
**Features:**
- System tray icon (4 states)
- Event queue consumer thread
- Toast notifications (winotify)
- Menu controls (pause, resume, stats, settings, about, quit)
- Direct backend control methods

**3. Backend Thread:**
```
app/standalone/backend_thread.py (825 lines)
```
**Status:** ✅ Complete (Story 8.4)
**Features:**
- Flask app in daemon thread
- CV pipeline with MediaPipe
- Alert manager
- Callback registration system
- Priority event queue producer
- Thread-safe SharedState
- Direct control methods

**4. Configuration:**
```
app/standalone/config.py (200 lines)
```
**Status:** ✅ Complete (Story 8.5)
**Features:**
- get_appdata_dir(), get_database_path(), get_log_dir()
- load_config(), save_config()
- DEFAULT_CONFIG with IPC section

**5. Windows Integration (Story 8.3):**
```
app/standalone/camera_windows.py
app/standalone/camera_selection_dialog.py
app/standalone/camera_permissions.py
app/standalone/camera_error_handler.py
```
**Status:** ✅ Complete (Story 8.3)
**Features:**
- DirectShow camera capture (cv2.VideoCapture)
- Camera selection UI
- Permission handling
- Error recovery

### **Epic 7 Build Infrastructure (Pattern Reference)**

**1. PyInstaller Spec (Client):**
```
build/windows/deskpulse_client.spec (79 lines)
```
**Pattern:** Entry point, hiddenimports, excludes, icon, one-folder mode
**Reusable:** Structure, UPX compression, excludes pattern
**Changes Needed:** Different entry point, different hiddenimports (ADD backend, REMOVE client)

**2. Build Script (PowerShell):**
```
build/windows/build.ps1 (240 lines)
```
**Pattern:** Prerequisites check, clean, build, verify, error handling
**Reusable:** ~80% of script logic
**Changes Needed:** Different spec file path, different output validation

**3. Inno Setup Script:**
```
build/windows/installer.iss (134 lines)
```
**Pattern:** Setup config, files, icons, tasks, uninstall code
**Reusable:** ~90% of script
**Changes Needed:** Different app name, version 2.0.0, source path

**4. Icon Asset:**
```
assets/windows/icon_professional.ico
```
**Status:** ✅ Exists (Epic 7)
**Reuse:** Yes (same icon for standalone edition)

---

## Acceptance Criteria

### **AC1: PyInstaller Spec File for Standalone Edition**

**Given** Story 8.5 code is complete
**When** developer creates PyInstaller spec file
**Then** spec file bundles entire standalone application:

**Requirements:**

- **File Location:** `build/windows/standalone.spec`
- **Entry Point:** `app/standalone/__main__.py` (Story 8.5)
- **Build Mode:** One-folder (`--onedir`, NOT `--onefile`)
  - **Rationale:** Faster startup (~3-5s vs ~10-15s), fewer antivirus false positives, easier debugging
  - **Source:** [PyInstaller Operating Mode Docs](https://pyinstaller.org/en/stable/operating-mode.html)
- **Console Mode:** `console=False` (windowed GUI, no console window)
- **UPX Compression:** `upx=True` (reduce size ~25-40%)
- **Icon:** `assets/windows/icon_professional.ico` (multi-resolution)

**PyInstaller Hook Strategy:**

Epic 7 uses `build/windows/hook-app.py` to EXCLUDE server modules (Flask, cv2, app.api) from client build. Story 8.6 needs the OPPOSITE approach: INCLUDE server modules, EXCLUDE client modules.

**Options:**
1. **Remove hook-app.py temporarily** during standalone build (simpler, recommended)
2. **Create hook-app-standalone.py** with inverted excludes (more complex)

**Recommendation:** Option 1 - Remove or rename `hook-app.py` before building standalone, restore after build.

**Validation:**
- [ ] Verify no import conflicts between `app.windows_client` and `app.standalone`
- [ ] Confirm server modules (Flask, cv2, app.api) bundled correctly
- [ ] Ensure client-only modules (socketio.client) NOT bundled

---

**Hidden Imports (CRITICAL - Standalone Edition Includes Backend):**
```python
hiddenimports=[
    # === Core Application ===
    'app.standalone.__main__',
    'app.standalone.backend_thread',
    'app.standalone.tray_app',
    'app.standalone.config',

    # === Backend Framework (INCLUDED - Story 8.1) ===
    'flask',
    'flask.app',
    'flask.blueprints',
    'flask.templating',

    # 'flask_socketio',  # OPTIONAL: Only needed if web dashboard desired
    # DECISION: Exclude flask_socketio for Story 8.6 (tray-only, no web UI)
    # BENEFIT: -5 MB installer size, simpler dependencies, faster startup
    # TRADE-OFF: Cannot access web dashboard at http://localhost:5000
    # RECOMMENDATION: Exclude for v2.0.0, add in future if web UI needed
    # NOTE: app/__init__.py uses try/except import (lines 10-13), handles absence gracefully

    'flask_talisman',  # REQUIRED: Unconditional import in app/__init__.py line 3
                       # Even though Talisman() not called in standalone mode (standalone_mode=True),
                       # import statement executes at module load time in create_app()
                       # CANNOT EXCLUDE: Would cause ImportError when backend_thread.py imports create_app

    # === Computer Vision (INCLUDED - Story 8.2/8.3) ===
    'cv2',
    'cv2.data',  # Haar cascades, models

    # MediaPipe - EXACT VERSION REQUIRED (Story 8.2 Tasks API migration)
    # requirements.txt locks versions:
    #   - x64/AMD64: mediapipe==0.10.31
    #   - ARM64: mediapipe==0.10.18
    # CRITICAL: PyInstaller bundling behavior may be version-specific
    # VALIDATION: After build, test pose detection to ensure models load correctly
    'mediapipe',
    'mediapipe.python',
    'mediapipe.tasks',
    'mediapipe.tasks.python',
    'mediapipe.tasks.python.vision',

    'numpy',
    'numpy.core',
    'numpy.core._multiarray_umath',

    # === System Tray (Story 8.5) ===
    'pystray',
    'pystray._win32',

    # === Image Processing ===
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',

    # === Toast Notifications (Story 8.5) ===
    'winotify',
    'winotify.audio',

    # === Windows API (Story 8.5) ===
    'win32event',
    'win32api',
    'winerror',
    'ctypes',

    # === Database ===
    'sqlite3',

    # === Standard Library (explicit inclusion) ===
    'queue',
    'threading',
    'json',
    'logging',
    'logging.handlers',
    'pathlib',
    'datetime',
    'time',
    'signal',
]
```

**Data Files to Bundle:**
```python
datas=[
    # Application icon (multi-resolution)
    ('assets/windows/icon_professional.ico', 'assets'),

    # MediaPipe models - VERIFY NO EXTERNAL FILES NEEDED
    # mediapipe==0.10.31 (x64) bundles .tflite models internally in package
    # VALIDATION: After build, test pose detection to ensure models accessible
    # If ImportError or "model file not found", may need explicit data bundling:
    #   - Check mediapipe package for .tflite file locations
    #   - Add: (mediapipe_model_path, 'mediapipe/modules/pose_landmark')
]
```

**Packages to Exclude (NOT needed in standalone):**
```python
excludes=[
    # Development/testing (never bundle)
    'pytest',
    'pytest-cov',
    'pytest-flask',
    'unittest',

    # Documentation
    'sphinx',
    'docutils',

    # Network SocketIO client (Epic 7 only)
    'socketio.client',  # Standalone uses SERVER, not client
    'engineio.client',

    # Linux-only packages
    'systemd',
    'systemd.journal',
    'sdnotify',
]
```

**Validation:**
- [ ] Spec file syntax valid (pyinstaller --help shows valid options)
- [ ] Entry point correct: `app/standalone/__main__.py`
- [ ] All backend packages in hiddenimports (Flask, OpenCV, MediaPipe)
- [ ] All Windows packages in hiddenimports (pystray, winotify, pywin32)
- [ ] Icon file path correct
- [ ] Excludes list prevents unnecessary bloat
- [ ] One-folder mode configured (`exe.exclude_binaries=True`)
- [ ] UPX compression enabled

**Source:** Epic 7 `deskpulse_client.spec` pattern (adapted for standalone with backend included)

---

### **AC2: Build Automation Script (PowerShell/Batch)**

**Given** the spec file exists
**When** developer runs build script
**Then** automated build process executes with validation:

**Script Location:** `build/windows/build_standalone.ps1`

**Pattern:** Adapt Epic 7 `build.ps1` (240 lines, ~80% reusable)
**Reference:** `/home/dev/deskpulse/build/windows/build.ps1`

**Changes from Epic 7:**

**1. Prerequisites Check (ADD):**
- **PowerShell Execution Policy Check:**
  ```powershell
  $policy = Get-ExecutionPolicy
  if ($policy -eq "Restricted" -or $policy -eq "AllSigned") {
      Write-Host "WARNING: Execution policy restrictive: $policy" -ForegroundColor Yellow
      Write-Host "Run with: powershell -ExecutionPolicy Bypass -File build_standalone.ps1"
      # Prompt user to continue or exit
  }
  ```
- **Story 8.5 Entry Point Check:**
  ```powershell
  if (-not (Test-Path "app/standalone/__main__.py")) {
      Write-Host "ERROR: Story 8.5 must be complete first" -ForegroundColor Red
      exit 1
  }
  ```
- **Backend Dependencies Check:**
  ```powershell
  $backendPackages = @('flask', 'opencv-python', 'mediapipe')
  foreach ($pkg in $backendPackages) {
      pip show $pkg | Out-Null
      if ($LASTEXITCODE -ne 0) {
          Write-Host "ERROR: Backend package missing: $pkg" -ForegroundColor Red
          exit 1
      }
  }
  ```

**2. PyInstaller Hook Handling (NEW):**
```powershell
# CRITICAL: Epic 7 hook-app.py EXCLUDES server modules (Flask, cv2)
# Story 8.6 needs server modules INCLUDED
# Solution: Temporarily rename hook to prevent conflicts

if (Test-Path "build/windows/hook-app.py") {
    Write-Host "Renaming Epic 7 hook (excludes server modules)..." -ForegroundColor Yellow
    Rename-Item -Path "build/windows/hook-app.py" -NewName "hook-app.py.epic7.bak"
}
```

**3. Spec File Path:**
- Epic 7: `build/windows/deskpulse_client.spec`
- Story 8.6: `build/windows/standalone.spec`

**4. Output Directory:**
- Epic 7: `dist/DeskPulse/`
- Story 8.6: `dist/DeskPulse-Standalone/`

**5. Dependency Installation:**
```powershell
# Install BOTH requirements files (backend + windows)
pip install -r requirements.txt
pip install -r requirements-windows.txt
```

**6. Build Verification (ENHANCE):**
```powershell
# Verify backend DLLs bundled (cv2 for DirectShow)
$backendDLLs = @(
    "dist/DeskPulse-Standalone/_internal/cv2/",  # OpenCV DLLs
    "dist/DeskPulse-Standalone/_internal/mediapipe/"  # MediaPipe models
)
# Check and warn if missing
```

**7. Restore Epic 7 Hook (POST-BUILD):**
```powershell
# Restore Epic 7 hook after standalone build
if (Test-Path "build/windows/hook-app.py.epic7.bak") {
    Rename-Item -Path "build/windows/hook-app.py.epic7.bak" -NewName "hook-app.py"
}
```

**Script Structure (from Epic 7):**
1. Prerequisites check (Python version, architecture, PyInstaller, icon, **execution policy**, **Story 8.5**)
2. **PyInstaller hook handling** (rename Epic 7 hook)
3. Clean previous builds (`dist/`, `build/`, `__pycache__`)
4. Install/verify dependencies (**both requirements files**)
5. Execute PyInstaller with logging
6. Verify build output (exe exists, measure size, **check backend DLLs**)
7. **Restore Epic 7 hook**
8. Display summary with next steps

**Validation:**
- [ ] PowerShell execution policy checked and bypass instructions provided
- [ ] Story 8.5 entry point verified (app/standalone/__main__.py exists)
- [ ] Epic 7 hook temporarily renamed to prevent server module exclusion
- [ ] Both requirements files installed (requirements.txt + requirements-windows.txt)
- [ ] Backend packages verified (flask, opencv-python, mediapipe)
- [ ] PyInstaller executes without errors
- [ ] Build log captured to: build/windows/build_standalone.log
- [ ] Executable verified: dist/DeskPulse-Standalone/DeskPulse.exe
- [ ] Backend DLLs checked (cv2, mediapipe directories)
- [ ] Epic 7 hook restored after build
- [ ] Distribution size measured (expected: 200-300 MB)
- [ ] Summary displays next steps

**Full Implementation:** See Task 2 (lines 1070-1131) for detailed subtasks

**Source:** Epic 7 `build.ps1` pattern (adapted for standalone with backend bundling)

---

### **AC3: Inno Setup Installer Configuration**

**Given** PyInstaller build succeeds
**When** developer runs Inno Setup compiler
**Then** professional Windows installer created:

**Installer Script Location:** `build/windows/installer_standalone.iss`

**Installer Configuration:**

**[Setup] Section:**
```ini
[Setup]
; Application information
AppName=DeskPulse Standalone Edition
AppVersion=2.0.0
AppPublisher=DeskPulse Team
AppPublisherURL=https://github.com/EmekaOkaforTech/deskpulse
AppSupportURL=https://github.com/EmekaOkaforTech/deskpulse/issues
AppUpdatesURL=https://github.com/EmekaOkaforTech/deskpulse/releases

; Installation directories
DefaultDirName={autopf}\DeskPulse
DefaultGroupName=DeskPulse
DisableProgramGroupPage=yes

; Output configuration
OutputDir=build\windows\Output
OutputBaseFilename=DeskPulse-Standalone-Setup-v2.0.0
Compression=lzma2/ultra64
SolidCompression=yes

; Expected installer size: See Dev Notes "File Size Expectations" (lines 1601-1638)
; Target: ≤100 MB | Realistic: 80-120 MB | Max acceptable: ≤150 MB

; Architecture
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Visual style
WizardStyle=modern
SetupIconFile=assets\windows\icon_professional.ico
UninstallDisplayIcon={app}\DeskPulse.exe
UninstallDisplayName=DeskPulse Standalone Edition

; Privileges (admin required for Program Files)
PrivilegesRequired=admin

; Version info
VersionInfoVersion=2.0.0.0
VersionInfoCompany=DeskPulse Team
VersionInfoDescription=DeskPulse Standalone Edition Installer
VersionInfoCopyright=Copyright (C) 2026 DeskPulse Team
VersionInfoProductName=DeskPulse Standalone Edition
VersionInfoProductVersion=2.0.0
```

**[Files] Section:**
```ini
[Files]
; Copy entire PyInstaller distribution (one-folder mode)
Source: "..\..\dist\DeskPulse-Standalone\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
```

**[Icons] Section:**
```ini
[Icons]
; Start Menu shortcuts
Name: "{group}\DeskPulse"; Filename: "{app}\DeskPulse.exe"
Name: "{group}\Uninstall DeskPulse"; Filename: "{uninstallexe}"

; Auto-start shortcut (created only if user selects task)
Name: "{commonstartup}\DeskPulse"; Filename: "{app}\DeskPulse.exe"; Tasks: startupicon
```

**[Tasks] Section:**
```ini
[Tasks]
; Auto-start option (unchecked by default - user opt-in)
Name: "startupicon"; Description: "Start DeskPulse automatically when Windows starts"; GroupDescription: "Startup Options:"; Flags: unchecked
```

**[Run] Section:**
```ini
[Run]
; Launch application after installation (user can uncheck)
Filename: "{app}\DeskPulse.exe"; Description: "Launch DeskPulse"; Flags: nowait postinstall skipifsilent
```

**[Code] Section (Uninstall with User Data Preservation):**
```pascal
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
  DialogResult: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { User data directory }
    ConfigDir := ExpandConstant('{userappdata}\DeskPulse');

    if DirExists(ConfigDir) then
    begin
      { Prompt user with detailed explanation }
      DialogResult := MsgBox(
        'Do you want to delete your configuration, database, and logs?' + #13#10 + #13#10 +
        'Location: ' + ConfigDir + #13#10 + #13#10 +
        'This includes:' + #13#10 +
        '  • Configuration (config.json)' + #13#10 +
        '  • Posture database (deskpulse.db)' + #13#10 +
        '  • Application logs (logs/)' + #13#10 + #13#10 +
        'If you plan to reinstall DeskPulse, choose "No" to keep your data.',
        mbConfirmation,
        MB_YESNO
      );

      if DialogResult = IDYES then
      begin
        { User chose to delete data }
        if DelTree(ConfigDir, True, True, True) then
        begin
          MsgBox('Configuration, database, and logs deleted successfully.', mbInformation, MB_OK);
        end
        else
        begin
          MsgBox(
            'Failed to delete some files in:' + #13#10 +
            ConfigDir + #13#10 + #13#10 +
            'You may need to delete them manually.',
            mbError,
            MB_OK
          );
        end;
      end
      else
      begin
        { User chose to preserve data }
        MsgBox(
          'Configuration, database, and logs preserved at:' + #13#10 +
          ConfigDir + #13#10 + #13#10 +
          'Your data will be available if you reinstall DeskPulse.',
          mbInformation,
          MB_OK
        );
      end;
    end;
  end;
end;
```

**Installer Output:**
- **File:** `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
- **Expected Size:** 150-250 MB (compressed installer, includes full backend)
- **Supports:** Windows 10/11 (64-bit)

**Validation:**
- [ ] Installer builds without errors
- [ ] Installer size within expected range (150-250 MB)
- [ ] Installation wizard displays correctly (modern style)
- [ ] Auto-start checkbox available (unchecked by default)
- [ ] Installs to Program Files\DeskPulse
- [ ] Start Menu shortcuts created
- [ ] Post-install launch works
- [ ] Uninstaller prompts for user data deletion
- [ ] User data preservation option works ("No" → data preserved)
- [ ] User data deletion option works ("Yes" → data deleted)
- [ ] Clean uninstall (no orphaned registry keys or files)

**Source:** Epic 7 `installer.iss` pattern (adapted for standalone, ~90% reusable)

---

### **AC4: Application Starts on Clean Windows 10/11**

**Given** installer is built
**When** installed on clean Windows VM (no Python)
**Then** application starts and functions correctly:

**Requirements:**

**Test Environment:**
- Windows 10 22H2 (Build 19045) or Windows 11 22H2 (Build 22621)
- 64-bit architecture
- NO Python installed
- NO development tools installed
- Fresh VM or clean user account

**Installation Test:**
1. Download installer: `DeskPulse-Standalone-Setup-v2.0.0.exe`
2. Run installer (SmartScreen warning expected - unsigned software)
3. Click "More info" → "Run anyway"
4. Follow installation wizard
5. Check "Start DeskPulse automatically when Windows starts" (optional)
6. Complete installation
7. Launch DeskPulse from Start Menu

**Startup Validation:**
- [ ] Application launches within 5 seconds
- [ ] System tray icon appears (teal - monitoring)
- [ ] No console window appears
- [ ] No error dialogs appear
- [ ] Configuration created: `%APPDATA%\DeskPulse\config.json`
- [ ] Database created: `%APPDATA%\DeskPulse\deskpulse.db`
- [ ] Logs created: `%APPDATA%\DeskPulse\logs\deskpulse.log`

**Functional Validation:**
- [ ] Right-click tray icon → Menu appears
- [ ] "Pause Monitoring" → Icon turns gray
- [ ] "Resume Monitoring" → Icon turns teal
- [ ] "Today's Stats" → MessageBox displays stats
- [ ] "Settings" → Shows config.json path
- [ ] "About" → Shows version 2.0.0, platform info, GitHub link
- [ ] "Quit DeskPulse" → Confirmation dialog → Application exits cleanly

**Camera Validation (Bundled Mode Specific):**
- [ ] Camera enumeration works (DirectShow backend functional in packaged app)
- [ ] cv2.VideoCapture(index) succeeds with correct camera index
- [ ] Camera detection identical to Story 8.3 source mode (99 tests baseline)
- [ ] Camera selection dialog appears if multiple cameras (tkinter bundled correctly)
- [ ] Camera permission check works in packaged app context
- [ ] Graceful degradation if no camera (monitoring disabled, UI still works)
- [ ] Camera state changes reflected in tray icon and logs
- [ ] USB camera hotplug detection tested (connect camera after app start)

**Known Bundling Issues to Verify:**
- [ ] OpenCV cv2 DLLs bundled correctly (opencv_videoio_ffmpeg DLL for DirectShow)
- [ ] Windows registry access works for camera permission checks
- [ ] DirectShow backend selected correctly (verify in logs: "Using DirectShow backend")
- [ ] No ImportError for cv2, tkinter, or camera modules

**Performance Validation:**
- [ ] Memory usage: <255 MB after 5 minutes
- [ ] CPU usage: <10% idle, <35% during monitoring
- [ ] Startup time: <5 seconds (cold start)
- [ ] Shutdown time: <2 seconds (quit to process exit)
- [ ] No memory leaks (memory stable over 30 minutes)

**Error Handling Validation:**
- [ ] Corrupt config.json → Shows warning, uses defaults, logs error
- [ ] Camera disconnect → Graceful degradation, logs error, icon updates
- [ ] Disk full → Database writes fail gracefully, logs error
- [ ] Second instance launch → MessageBox "Already running", exits gracefully

**Source:** Epic 7 testing pattern, Story 8.5 acceptance criteria

---

### **AC5: Auto-Start Functionality**

**Given** user selected "Start automatically" during installation
**When** Windows starts or user logs in
**Then** DeskPulse launches automatically:

**Requirements:**

**Auto-Start Mechanism:**
- **Method:** Startup folder shortcut (simple, reliable, no registry edits)
- **Path:** `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DeskPulse.lnk`
- **Target:** `C:\Program Files\DeskPulse\DeskPulse.exe`
- **Alternative:** Registry run key (if startup folder fails)
  - **Key:** `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
  - **Value:** `DeskPulse` = `"C:\Program Files\DeskPulse\DeskPulse.exe"`

**Inno Setup Implementation:**
- Shortcut created via `[Icons]` section with `Tasks: startupicon`
- Task unchecked by default (user must opt-in)
- Only created if user checks checkbox during installation

**Validation:**
- [ ] Auto-start checkbox appears during installation
- [ ] Checkbox unchecked by default (user opt-in)
- [ ] If checked: Shortcut created in Startup folder
- [ ] If unchecked: No shortcut created
- [ ] After reboot: DeskPulse starts automatically (if enabled)
- [ ] Startup time: <5 seconds after login
- [ ] Tray icon appears within 10 seconds of desktop ready
- [ ] No error dialogs on startup
- [ ] Single instance check works (no duplicate launches)
- [ ] Uninstaller removes startup shortcut

**Manual Enable/Disable:**
- [ ] User can manually add shortcut to Startup folder
- [ ] User can manually remove shortcut to disable auto-start
- [ ] Settings menu explains auto-start configuration

**Source:** Epic 7 installer auto-start pattern

---

### **AC6: Professional Icon and Branding**

**Given** icon assets exist from Epic 7
**When** building standalone edition
**Then** professional branding applied consistently:

**Requirements:**

**Icon Asset:**
- **File:** `assets/windows/icon_professional.ico`
- **Status:** ✅ Exists (Epic 7)
- **Resolutions:** 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
- **Design:** Green posture icon (person silhouette with spine)
- **Format:** Windows ICO (multi-resolution, 32-bit RGBA)

**Icon Usage:**
- **Executable:** `DeskPulse.exe` icon (via PyInstaller spec)
- **System Tray:** Tray icon (Story 8.5 tray_app.py)
- **Installer:** Setup wizard icon (via Inno Setup)
- **Uninstaller:** Control Panel icon (via Inno Setup)
- **Shortcuts:** Start Menu and Startup folder (via Inno Setup)

**Branding Consistency:**
- **Application Name:** "DeskPulse" (no "Standalone" suffix in UI)
- **Version:** 2.0.0 (Story 8.5 __main__.py)
- **About Dialog:** Shows "DeskPulse - Standalone Edition\nVersion: 2.0.0"
- **Installer Name:** "DeskPulse Standalone Edition" (to distinguish from Epic 7 client)
- **Uninstall Name:** "DeskPulse Standalone Edition" (Control Panel)

**Validation:**
- [ ] Icon displays correctly in Windows Explorer
- [ ] Icon displays correctly in Task Manager
- [ ] Icon displays correctly in system tray (4 states: monitoring, paused, alert, disconnected)
- [ ] Icon displays correctly in taskbar (when minimized)
- [ ] Icon displays correctly in Start Menu
- [ ] Installer wizard displays icon
- [ ] Control Panel shows correct icon and name
- [ ] About dialog shows correct version and edition

**Source:** Epic 7 icon assets (reused), Story 8.5 branding

---

### **AC7: Build Documentation (README)**

**Given** build system is complete
**When** developer needs to build installer
**Then** comprehensive documentation exists:

**Documentation File:** `build/windows/README_STANDALONE.md`

**Required Sections:**

**1. Prerequisites:**
- **Operating System:** Windows 10 1803+ or Windows 11 (64-bit)
- Python 3.9+ (64-bit) - verify with `python --version`
- PyInstaller 6.0+ - auto-installed by build script
- Inno Setup 6 (optional, for installer) - download from jrsoftware.org
- All dependencies: `pip install -r requirements.txt requirements-windows.txt`

**2. Quick Build (Standalone .exe only):**
```powershell
# From project root
.\build\windows\build_standalone.ps1
```
**Output:** `dist/DeskPulse-Standalone/DeskPulse.exe`

**3. Full Build (Installer):**
```powershell
# Step 1: Build executable
.\build\windows\build_standalone.ps1

# Step 2: Create installer (requires Inno Setup)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
```
**Output:** `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`

**4. Testing Instructions:**
- **Standalone .exe:** Run on development machine first
- **Clean VM Test:** Copy `dist/DeskPulse-Standalone/` to VM, run `DeskPulse.exe`
- **Installer Test:** Install on clean VM, verify functionality, test auto-start, test uninstaller

**5. Troubleshooting:**
- **Common Build Errors:**
  - "ModuleNotFoundError" → Add to hiddenimports in spec file
  - "Icon file not found" → Verify `assets/windows/icon_professional.ico` exists
  - "DLL not found" → Verify pywin32 installed (`pip install pywin32`)

- **Common Runtime Errors:**
  - Application doesn't start → Check logs at `%APPDATA%\DeskPulse\logs\deskpulse.log`
  - "Failed to initialize backend" → Camera permission issue or missing MediaPipe
  - SmartScreen warning → Expected (unsigned), click "More info" → "Run anyway"

**6. Distribution Checklist:**
- [ ] Build installer: `DeskPulse-Standalone-Setup-v2.0.0.exe`
- [ ] Calculate SHA256 checksum: `certutil -hashfile <installer> SHA256`
- [ ] Test on clean Windows 10 VM
- [ ] Test on clean Windows 11 VM
- [ ] Create GitHub Release: `v2.0.0-standalone`
- [ ] Upload installer to GitHub Releases
- [ ] Add SHA256 checksum to release notes
- [ ] Document SmartScreen bypass instructions
- [ ] Update README.md with download link

**7. Code Signing Considerations:**
- **Current Status:** NOT code-signed (open-source project)
- **User Impact:** SmartScreen warning on first run
- **Bypass Instructions:** Click "More info" → "Run anyway"
- **Future:** Code signing certificate ($200-500/year) reduces warnings

**8. Performance Expectations:**

See Dev Notes "File Size Expectations" (lines 1601-1638) for detailed component breakdown.

**Summary:**
- **Installer Size:** 80-120 MB (target ≤100 MB, max ≤150 MB)
- **Installed Size:** 200-300 MB (one-folder distribution with full backend)
- **Startup Time:** <5s cold start (<2s warm), +1-2s acceptable degradation vs source
- **Memory:** <255 MB monitoring active, +20-50 MB acceptable degradation vs source
- **CPU:** <10% idle, <35% monitoring, +2-5% acceptable degradation vs source
- **Build Time:** 2-5 minutes (PyInstaller + dependencies)

See AC9 for performance regression testing (bundled vs source comparison).

**Validation:**
- [ ] README covers all build steps
- [ ] README includes troubleshooting section
- [ ] README documents distribution checklist
- [ ] README explains SmartScreen warning
- [ ] README includes performance expectations
- [ ] README tested by following instructions on clean machine

**Source:** Epic 7 `build/windows/README.md` pattern (adapted for standalone)

---

### **AC8: Distribution Package Complete**

**Given** installer is built and tested
**When** preparing for distribution
**Then** release package includes all necessary components:

**Distribution Checklist:**

**1. Build Artifacts:**
- [ ] Standalone executable: `dist/DeskPulse-Standalone/DeskPulse.exe`
- [ ] Installer: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
- [ ] Build log: `build/windows/build_standalone.log`

**2. Checksums:**
```powershell
# Calculate SHA256 for installer
certutil -hashfile build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe SHA256

# Expected output format:
# SHA256 hash of build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe:
# <64-character hex string>
```
- [ ] SHA256 checksum calculated
- [ ] Checksum added to release notes
- [ ] Checksum verified on clean download

**3. GitHub Release:**
- [ ] Tag created: `v2.0.0-standalone`
- [ ] Release title: "DeskPulse v2.0.0 - Standalone Windows Edition"
- [ ] Release notes written (template below)
- [ ] Installer uploaded as release asset
- [ ] SHA256 checksum in release notes
- [ ] SmartScreen bypass instructions in release notes
- [ ] Download link tested

**4. Release Notes Template:**
```markdown
# DeskPulse v2.0.0 - Standalone Windows Edition

## Overview

Complete posture monitoring system for Windows - no Raspberry Pi needed!

## Downloads

- **Windows Installer (64-bit)**: [DeskPulse-Standalone-Setup-v2.0.0.exe](link)
  - Size: ~200 MB
  - SHA256: `<checksum>`

## What's Included

- ✅ Full backend (Flask, OpenCV, MediaPipe)
- ✅ Real-time posture monitoring using your PC webcam
- ✅ System tray integration with toast notifications
- ✅ Analytics and progress tracking
- ✅ Auto-start option (opt-in during install)
- ✅ No Python or dependencies required

## Installation

1. Download `DeskPulse-Standalone-Setup-v2.0.0.exe`
2. Run installer (SmartScreen warning - see below)
3. Follow installation wizard
4. Optional: Enable "Start automatically when Windows starts"
5. Launch DeskPulse from Start Menu

## Requirements

- Windows 10 (22H2) or Windows 11 (64-bit)
- Webcam (built-in or USB)
- ~300 MB disk space
- No Python installation required

## SmartScreen Warning

Windows SmartScreen may warn about this application because it's not code-signed.
This is **normal** for open-source software.

**To proceed:**
1. Click "More info"
2. Click "Run anyway"
3. This warning won't appear again

**Why unsigned?**
Code signing certificates cost $200-500/year. As an open-source project, we prioritize code transparency over certificates. You can verify our source code at: https://github.com/EmekaOkaforTech/deskpulse

## Support

- **Issues**: https://github.com/EmekaOkaforTech/deskpulse/issues
- **Documentation**: https://github.com/EmekaOkaforTech/deskpulse#readme
- **Discussions**: https://github.com/EmekaOkaforTech/deskpulse/discussions
```

**5. Documentation Updates:**
- [ ] README.md updated with standalone edition section
- [ ] README.md includes download link
- [ ] README.md documents system requirements
- [ ] README.md explains differences from Pi edition
- [ ] CHANGELOG.md updated with v2.0.0 release notes

**Validation:**
- [ ] Installer uploaded to GitHub Releases
- [ ] SHA256 checksum verified
- [ ] Release notes comprehensive and accurate
- [ ] Download link tested on external machine
- [ ] Installation tested from GitHub download
- [ ] SmartScreen bypass instructions work
- [ ] README.md updated

**Source:** Epic 7 distribution pattern, GitHub Release best practices

---

### **AC9: Performance Regression Testing (Bundled vs Source)**

**Given** bundled executable from PyInstaller
**When** comparing performance to Story 8.5 source mode
**Then** acceptable performance degradation documented and validated:

**Requirements:**

**Baseline Measurement (Source Mode - Story 8.5):**

Measure Story 8.5 source mode first (before building Story 8.6):
- **Memory:** 80-150 MB typical running, <255 MB max (from Story 8.5 validation)
- **CPU:** 2-5% idle, 10-20% monitoring, <35% max
- **Startup:** 2-3s typical, <5s max
- **Alert Latency:** 0.16ms avg (measured Story 8.4), <50ms max
- **Shutdown:** 0.5-1.5s typical, <2s max

**Bundled Mode Measurement (Story 8.6):**

Run same measurements on bundled .exe (dist/DeskPulse-Standalone/DeskPulse.exe):
- Launch executable on development machine
- Run 30-minute stability test (same as Story 8.5)
- Measure performance metrics using Task Manager + Performance Monitor
- Compare results side-by-side with Story 8.5 baseline

**Acceptable Degradation Ranges:**

PyInstaller bundling adds overhead due to import resolution, module loading, and compressed archive extraction:

| Metric | Source (8.5) | Bundled (8.6) Acceptable | Max Degradation | Absolute Limit |
|--------|-------------|--------------------------|-----------------|----------------|
| **Memory** | 80-150 MB | +20-50 MB | +50 MB | <255 MB |
| **CPU (Idle)** | 2-5% | +1-3% | +3% | <10% |
| **CPU (Monitor)** | 10-20% | +2-5% | +5% | <35% |
| **Startup (Cold)** | 2-3s | +1-2s | +2s | <5s |
| **Alert Latency** | 0.16ms | +5-10ms | +10ms | <50ms |
| **Shutdown** | 0.5-1.5s | +0.5s | +0.5s | <2s |

**Validation Procedure:**

**1. Source Mode Baseline (Run First):**
```powershell
# From project root
python -m app.standalone

# Let run for 30 minutes
# Measure in Task Manager:
#   - Memory (Private Working Set)
#   - CPU % (average over 30 min)
# Measure startup: stopwatch from launch to tray icon appears
# Measure shutdown: stopwatch from quit click to process exit
# Check logs for alert latency: grep "alert_latency_ms" logs/deskpulse.log
```

**2. Bundled Mode Measurement (After Build):**
```powershell
# From dist/DeskPulse-Standalone/
.\DeskPulse.exe

# Same measurements as source mode
# Document in validation report
```

**3. Comparison Analysis:**
```markdown
### Performance Comparison (Source vs Bundled)

| Metric | Source | Bundled | Delta | Within Acceptable? |
|--------|--------|---------|-------|-------------------|
| Memory | 145 MB | 180 MB | +35 MB | ✅ (+35 < +50) |
| CPU (Idle) | 3.2% | 5.1% | +1.9% | ✅ (+1.9 < +3) |
| CPU (Monitor) | 18% | 22% | +4% | ✅ (+4 < +5) |
| Startup | 2.8s | 4.2s | +1.4s | ✅ (+1.4 < +2) |
| Alert Latency | 0.18ms | 8.5ms | +8.3ms | ✅ (+8.3 < +10) |
| Shutdown | 1.1s | 1.4s | +0.3s | ✅ (+0.3 < +0.5) |

**Verdict:** All metrics within acceptable degradation ranges ✅
```

**Validation Checklist:**
- [ ] Source mode baseline measured and documented
- [ ] Bundled mode measured with identical test procedure
- [ ] 30-minute stability test completed for both modes
- [ ] All metrics compared side-by-side
- [ ] Memory degradation ≤ +50 MB (absolute limit: <255 MB)
- [ ] CPU degradation ≤ +5% monitoring (absolute limit: <35%)
- [ ] Startup degradation ≤ +2s (absolute limit: <5s)
- [ ] Alert latency degradation ≤ +10ms (absolute limit: <50ms)
- [ ] Shutdown degradation ≤ +0.5s (absolute limit: <2s)
- [ ] If any metric exceeds acceptable range, root cause identified
- [ ] Performance comparison documented in validation report

**If Degradation Exceeds Acceptable Range:**

**Optimization Strategies:**
- **Memory:** Check for duplicate DLLs, use `--exclude-module` for unused packages
- **Startup:** Verify one-folder mode (not one-file), check for slow imports
- **Alert Latency:** Profile with cProfile, check for lazy imports in hot path
- **CPU:** Check for background threads spinning, verify daemon threads

**Root Cause Investigation:**
```powershell
# Check for duplicate modules
pyinstaller --log-level=DEBUG build/windows/standalone.spec 2>&1 | Select-String "duplicate"

# Measure import times
python -m app.standalone --profile-imports

# Check bundle size by module
python -m PyInstaller.utils.cliutils.makespec --analyze build/windows/standalone.spec
```

**Validation:**
- [ ] Performance regression testing completed
- [ ] Source vs bundled comparison documented
- [ ] All degradations within acceptable ranges
- [ ] Absolute limits not exceeded (<255 MB, <35% CPU, <5s startup, <50ms latency)
- [ ] Comparison table included in validation report (Task 4/5 deliverable)

**Source:** Story 8.5 performance baselines, Story 8.4 latency measurements, PyInstaller overhead analysis

---

## Tasks / Subtasks

### **Task 1: Create PyInstaller Spec File** (AC: 1)
**Priority:** P0 (Blocker)

- [x] 1.1 Create `build/windows/standalone.spec`
  - Use Epic 7 `deskpulse_client.spec` as template
  - Change entry point: `['app/standalone/__main__.py']`
  - Change output name: `name='DeskPulse'` (will create DeskPulse.exe)
  - Keep one-folder mode: `exclude_binaries=True` in EXE()
  - Keep UPX compression: `upx=True`
  - Icon path: `icon='assets/windows/icon_professional.ico'`

- [ ] 1.2 Configure hiddenimports for standalone edition
  - **ADD backend packages:**
    - `'flask'`, `'flask.app'`, `'flask.blueprints'`
    - `'flask_socketio'` (for optional web dashboard)
    - `'flask_talisman'` (enterprise security)
    - `'cv2'`, `'cv2.data'`
    - `'mediapipe'`, `'mediapipe.tasks.python.vision'`
    - `'numpy'`, `'numpy.core._multiarray_umath'`
    - `'sqlite3'`
  - **ADD Windows packages:**
    - `'pystray'`, `'pystray._win32'`
    - `'PIL'`, `'PIL.Image'`, `'PIL.ImageDraw'`
    - `'winotify'`, `'winotify.audio'`
    - `'win32event'`, `'win32api'`, `'winerror'`
  - **ADD app.standalone modules:**
    - `'app.standalone.__main__'`
    - `'app.standalone.backend_thread'`
    - `'app.standalone.tray_app'`
    - `'app.standalone.config'`
    - `'app.standalone.camera_windows'` (Story 8.3)
  - **REMOVE Epic 7 client-only:**
    - Remove `'socketio.client'`, `'engineio.client'` (standalone uses server, not client)

- [ ] 1.3 Configure excludes list
  - Exclude development: `'pytest'`, `'pytest-cov'`, `'unittest'`
  - Exclude Linux-only: `'systemd'`, `'sdnotify'`
  - Exclude client packages: `'socketio.client'`, `'engineio.client'`
  - Keep `'flask_socketio'` (server, needed for optional dashboard)

- [ ] 1.4 Configure data files
  - Bundle icon: `('assets/windows/icon_professional.ico', 'assets')`
  - Check if MediaPipe needs external .tflite models (usually bundled in package)

- [ ] 1.5 Validate spec file syntax
  - Run: `pyinstaller --help` to verify options
  - Check pathex points to project root
  - Verify icon path is correct
  - Ensure console=False (no console window)

**Estimated Complexity:** 3 hours

**Code Location:** `/home/dev/deskpulse/build/windows/standalone.spec` (NEW - ~120 lines)

**Pattern References:**
- Epic 7 spec: `/home/dev/deskpulse/build/windows/deskpulse_client.spec` (79 lines)
- PyInstaller docs: https://pyinstaller.org/en/stable/spec-files.html

---

### **Task 2: Create Build Automation Script** (AC: 2)
**Priority:** P0 (Blocker)

- [ ] 2.1 Create `build/windows/build_standalone.ps1` or `.bat`
  - Use Epic 7 `build.ps1` as template (~240 lines)
  - Change spec file path: `build/windows/standalone.spec`
  - Change output directory: `dist/DeskPulse-Standalone`
  - Add backend dependency checks (Flask, OpenCV, MediaPipe)

- [ ] 2.2 Implement prerequisites check
  - Verify Python 3.9+ (64-bit)
  - Check PyInstaller available (auto-install if missing)
  - Verify icon file: `assets/windows/icon_professional.ico`
  - Verify Story 8.5 entry point: `app/standalone/__main__.py`
  - Check working directory is project root

- [ ] 2.3 Implement clean step
  - Remove `dist/DeskPulse-Standalone/` (if exists)
  - Remove `build/DeskPulse-Standalone/` (PyInstaller cache)
  - Remove `__pycache__` directories
  - Log clean operations

- [ ] 2.4 Implement dependency installation
  - Run: `pip install -r requirements.txt`
  - Run: `pip install -r requirements-windows.txt`
  - Verify critical packages: Flask, opencv-python, mediapipe, pystray, winotify, pywin32
  - Log dependency verification

- [ ] 2.5 Implement PyInstaller build
  - Run: `pyinstaller build/windows/standalone.spec`
  - Capture output to: `build/windows/build_standalone.log`
  - Check exit code (0 = success)
  - Display errors if build fails

- [ ] 2.6 Implement build verification
  - Check `dist/DeskPulse-Standalone/DeskPulse.exe` exists
  - Measure executable size (log to console)
  - Count total files in distribution
  - Calculate total distribution size
  - Verify critical DLLs bundled (python313.dll or python39.dll)

- [ ] 2.7 Implement build summary
  - Display success banner
  - Show executable path and size
  - Show total distribution size and file count
  - Show build log path
  - Display next steps (test, create installer)

- [ ] 2.8 Implement error handling
  - Python not found → Display install instructions
  - Python not 64-bit → Display error, exit
  - Icon not found → Display error, exit
  - Entry point not found → Display "Story 8.5 required", exit
  - PyInstaller build failed → Display log path, common issues, exit
  - Executable not created → Display error, exit

**Estimated Complexity:** 4 hours

**Code Location:** `/home/dev/deskpulse/build/windows/build_standalone.ps1` (NEW - ~280 lines)

**Pattern References:**
- Epic 7 script: `/home/dev/deskpulse/build/windows/build.ps1` (240 lines, ~80% reusable)

---

### **Task 3: Create Inno Setup Installer Script** (AC: 3)
**Priority:** P0 (Blocker)

- [ ] 3.1 Create `build/windows/installer_standalone.iss`
  - Use Epic 7 `installer.iss` as template (134 lines)
  - Change app name: `AppName=DeskPulse Standalone Edition`
  - Change version: `AppVersion=2.0.0`
  - Change source path: `Source: "..\..\dist\DeskPulse-Standalone\*"`
  - Change output filename: `OutputBaseFilename=DeskPulse-Standalone-Setup-v2.0.0`

- [ ] 3.2 Configure [Setup] section
  - Update all AppName references to "DeskPulse Standalone Edition"
  - Update version to 2.0.0
  - Update publisher URL: `https://github.com/EmekaOkaforTech/deskpulse`
  - Keep architecture: x64 only
  - Keep compression: lzma2/ultra64
  - Keep icon: `assets\windows\icon_professional.ico`

- [ ] 3.3 Configure [Files] section
  - Source: `..\..\dist\DeskPulse-Standalone\*`
  - DestDir: `{app}`
  - Flags: `ignoreversion recursesubdirs createallsubdirs`

- [ ] 3.4 Configure [Icons] section
  - Start Menu: `DeskPulse` → `{app}\DeskPulse.exe`
  - Uninstall: `Uninstall DeskPulse` → `{uninstallexe}`
  - Auto-start: `{commonstartup}\DeskPulse` (conditional on task)

- [ ] 3.5 Configure [Tasks] section
  - Auto-start option: `startupicon`
  - Description: "Start DeskPulse automatically when Windows starts"
  - Flags: `unchecked` (user opt-in)

- [ ] 3.6 Configure [Run] section
  - Post-install launch: `{app}\DeskPulse.exe`
  - Flags: `nowait postinstall skipifsilent`
  - Description: "Launch DeskPulse"

- [ ] 3.7 Implement [Code] section for uninstall
  - Copy Epic 7 `CurUninstallStepChanged` procedure
  - Update config path: `{userappdata}\DeskPulse`
  - Update prompt text to include database: "Configuration, database, and logs"
  - Test "Yes" path (delete all data)
  - Test "No" path (preserve data)

- [ ] 3.8 Test Inno Setup compilation
  - Run: `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss`
  - Verify installer created: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
  - Measure installer size (expected: 150-250 MB compressed)

**Estimated Complexity:** 2 hours

**Code Location:** `/home/dev/deskpulse/build/windows/installer_standalone.iss` (NEW - ~150 lines)

**Pattern References:**
- Epic 7 installer: `/home/dev/deskpulse/build/windows/installer.iss` (134 lines, ~90% reusable)

---

### **Task 4: Test on Clean Windows 10 VM** (AC: 4)
**Priority:** P0 (Blocker)

**CRITICAL:** This task requires actual Windows 10 PC or VM.

- [ ] 4.1 Setup clean Windows 10 VM
  - Windows 10 22H2 (Build 19045) or later
  - 64-bit architecture
  - NO Python installed
  - NO development tools
  - Verify clean state: `python --version` should fail

- [ ] 4.2 Install DeskPulse
  - Download installer: `DeskPulse-Standalone-Setup-v2.0.0.exe`
  - Run installer (SmartScreen warning expected)
  - Click "More info" → "Run anyway"
  - Complete installation wizard
  - Launch DeskPulse from Start Menu

- [ ] 4.3 Test startup
  - Application launches within 5 seconds
  - System tray icon appears
  - No console window
  - No error dialogs
  - Check %APPDATA%\DeskPulse created
  - Check config.json, deskpulse.db, logs/deskpulse.log exist

- [ ] 4.4 Test functionality
  - Right-click tray icon → Menu appears
  - Test all menu items (pause, resume, stats, settings, about, quit)
  - Test camera detection (if VM has webcam)
  - Test toast notifications (trigger alert)
  - Verify monitoring works end-to-end

- [ ] 4.5 Test auto-start
  - Uninstall DeskPulse
  - Reinstall with "Start automatically" checked
  - Reboot VM
  - Verify DeskPulse starts automatically
  - Tray icon appears within 10 seconds

- [ ] 4.6 Test uninstaller
  - Run uninstaller from Control Panel
  - Verify user data prompt appears
  - Test "No" → Verify data preserved at %APPDATA%\DeskPulse
  - Reinstall, uninstall again
  - Test "Yes" → Verify data deleted
  - Verify Program Files directory removed
  - Verify Start Menu shortcuts removed
  - Verify no orphaned registry keys

- [ ] 4.7 Measure performance
  - Startup time: <5 seconds
  - Memory usage: <255 MB after 5 minutes
  - CPU usage: <10% idle, <35% monitoring
  - Run 30-minute stability test (0 crashes)

- [ ] 4.8 Create validation report
  - Document test environment (Windows version, build)
  - Document all test results (pass/fail)
  - Document performance metrics
  - Document any issues found
  - Save as: `docs/sprint-artifacts/validation-report-8-6-windows10-YYYY-MM-DD.md`

**Estimated Complexity:** 4 hours (includes Windows VM setup and testing)

**Deliverable:** `docs/sprint-artifacts/validation-report-8-6-windows10-2026-01-XX.md`

---

### **Task 5: Test on Clean Windows 11 VM** (AC: 4)
**Priority:** P0 (Blocker)

**CRITICAL:** This task requires actual Windows 11 PC or VM.

- [ ] 5.1 Setup clean Windows 11 VM
  - Windows 11 22H2 (Build 22621) or later
  - 64-bit architecture
  - NO Python installed
  - NO development tools
  - Verify clean state

- [ ] 5.2 Repeat all tests from Task 4
  - Installation test
  - Startup test
  - Functionality test
  - Auto-start test
  - Uninstaller test
  - Performance test

- [ ] 5.3 Test Windows 11 specific features
  - Tray icon rendering (Windows 11 updated tray design)
  - Toast notifications (Windows 11 notification center)
  - High DPI displays (if available)
  - Multiple monitors (if available)

- [ ] 5.4 Create validation report
  - Document test environment
  - Document all test results
  - Compare with Windows 10 results
  - Document any Windows 11 specific issues
  - Save as: `docs/sprint-artifacts/validation-report-8-6-windows11-YYYY-MM-DD.md`

**Estimated Complexity:** 3 hours (VM already setup pattern from Task 4)

**Deliverable:** `docs/sprint-artifacts/validation-report-8-6-windows11-2026-01-XX.md`

---

### **Task 6: Create Build Documentation** (AC: 7)
**Priority:** P1 (High)

- [ ] 6.1 Create `build/windows/README_STANDALONE.md`
  - Use Epic 7 `README.md` as template (464 lines)
  - Update for standalone edition (backend included)
  - Update prerequisites (backend dependencies)
  - Update build instructions (standalone.spec, build_standalone.ps1)
  - Update performance expectations (larger size, more memory)

- [ ] 6.2 Document prerequisites section
  - Operating system: Windows 10/11 (64-bit)
  - Python 3.9+ (64-bit)
  - PyInstaller 6.0+ (auto-installed)
  - Inno Setup 6 (optional)
  - All dependencies: requirements.txt + requirements-windows.txt

- [ ] 6.3 Document quick build section
  - Command: `.\build\windows\build_standalone.ps1`
  - Output: `dist/DeskPulse-Standalone/DeskPulse.exe`
  - Build time: 2-5 minutes
  - Distribution size: 200-300 MB

- [ ] 6.4 Document full build section (installer)
  - Step 1: Build executable
  - Step 2: Create installer with Inno Setup
  - Output: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
  - Installer size: 150-250 MB

- [ ] 6.5 Document testing instructions
  - Test standalone .exe on development machine
  - Test on clean Windows 10 VM
  - Test on clean Windows 11 VM
  - Test installer, auto-start, uninstaller

- [ ] 6.6 Document troubleshooting section
  - Common build errors (ModuleNotFoundError, icon missing, DLL issues)
  - Common runtime errors (startup fails, camera issues, SmartScreen)
  - Solutions for each error type

- [ ] 6.7 Document distribution checklist
  - Build installer
  - Calculate SHA256 checksum
  - Test on clean VMs
  - Create GitHub Release
  - Upload installer
  - Add checksum to release notes
  - Document SmartScreen bypass

- [ ] 6.8 Document code signing considerations
  - Current status: NOT signed
  - SmartScreen warning expected
  - Bypass instructions
  - Future: Code signing certificate cost and process

- [ ] 6.9 Document performance expectations
  - Installer size: 150-250 MB
  - Installed size: 200-300 MB
  - Startup time: <5 seconds
  - Memory: <255 MB
  - CPU: <10% idle, <35% monitoring

- [ ] 6.10 Test documentation
  - Follow README on clean machine
  - Verify all commands work
  - Verify troubleshooting section accurate
  - Update any errors or omissions

**Estimated Complexity:** 3 hours

**Code Location:** `/home/dev/deskpulse/build/windows/README_STANDALONE.md` (NEW - ~500 lines)

**Pattern References:**
- Epic 7 README: `/home/dev/deskpulse/build/windows/README.md` (464 lines, ~70% reusable)

---

### **Task 7: Prepare Distribution Package** (AC: 8)
**Priority:** P1 (High)

- [ ] 7.1 Calculate SHA256 checksum
  - Command: `certutil -hashfile build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe SHA256`
  - Save checksum to file: `build/windows/Output/SHA256SUMS.txt`
  - Verify checksum on test download

- [ ] 7.2 Create GitHub Release
  - Tag: `v2.0.0-standalone`
  - Title: "DeskPulse v2.0.0 - Standalone Windows Edition"
  - Draft release notes using template (AC8)
  - Include overview, downloads, installation, requirements, SmartScreen bypass

- [ ] 7.3 Upload installer as release asset
  - File: `DeskPulse-Standalone-Setup-v2.0.0.exe`
  - Verify upload successful
  - Test download link

- [ ] 7.4 Add SHA256 checksum to release notes
  - Copy checksum from SHA256SUMS.txt
  - Add to "Downloads" section of release notes
  - Verify checksum visible in published release

- [ ] 7.5 Update README.md
  - Add "Windows Standalone Edition" section
  - Document download link (GitHub Release)
  - Document system requirements
  - Explain differences from Pi edition (no Pi needed, uses PC webcam)
  - Add installation instructions with SmartScreen bypass

- [ ] 7.6 Update CHANGELOG.md
  - Add "v2.0.0 - Standalone Windows Edition" section
  - List all features (backend, CV pipeline, tray UI, notifications)
  - List all Story 8.1-8.6 changes
  - Document breaking changes (none for new edition)

- [ ] 7.7 Test distribution package
  - Download installer from GitHub Release
  - Verify SHA256 checksum matches
  - Install on clean VM
  - Verify full functionality
  - Test SmartScreen bypass instructions

- [ ] 7.8 Create distribution checklist document
  - Save as: `docs/sprint-artifacts/distribution-checklist-8-6.md`
  - Include all steps from AC8
  - Mark each item as completed
  - Document any issues or deviations

**Estimated Complexity:** 2 hours

**Deliverable:** GitHub Release `v2.0.0-standalone` with installer, checksum, and comprehensive release notes

---

## Dev Notes

### Enterprise-Grade Requirements (User Specified)

**Critical:** This story must meet enterprise standards:

- **No mock data** - All tests use real backend connections (follow Story 8.5 pattern)
- **Real backend bundled** - Flask, OpenCV, MediaPipe fully integrated
- **Production-ready installer** - Professional UX, clean uninstall, auto-start option
- **Complete validation** - Tested on actual Windows 10 AND Windows 11 hardware
- **Comprehensive documentation** - Build README, troubleshooting, distribution checklist
- **Performance baseline** - Meets Story 8.5 targets (<255 MB, <35% CPU, <5s startup)
- **Professional branding** - Consistent icon usage, proper versioning

### Critical Differences: Epic 7 vs Epic 8

**Epic 7 (Windows Client - Story 7.5):**
- **Architecture:** SocketIO client connecting to Pi backend
- **Entry Point:** `app/windows_client/__main__.py`
- **Spec File:** `build/windows/deskpulse_client.spec`
- **Size:** ~60-100 MB (client only, no backend)
- **Excludes:** Flask, OpenCV, MediaPipe (backend runs on Pi)
- **Includes:** socketio.client, engineio.client (network communication)
- **Purpose:** Remote control and notifications for Pi backend

**Epic 8 (Standalone Edition - Story 8.6):**
- **Architecture:** Standalone app with embedded backend (no network)
- **Entry Point:** `app/standalone/__main__.py` (Story 8.5)
- **Spec File:** `build/windows/standalone.spec` (NEW)
- **Size:** ~200-300 MB (full backend bundled)
- **Includes:** Flask, Flask-SocketIO (server), OpenCV, MediaPipe (backend embedded)
- **Excludes:** socketio.client, engineio.client (no network client needed)
- **Purpose:** Complete standalone posture monitoring on Windows PC

**Why This Matters:**
- Different hiddenimports (ADD backend, REMOVE client)
- Larger distribution size (3-5x Epic 7)
- Higher memory usage (backend runs locally)
- No network configuration needed (everything local)

### Hidden Imports: Comprehensive Analysis

**See AC1 (lines 217-297) for complete hiddenimports list.**

**Key Insights (Epic 7 vs Epic 8):**
- **Epic 7 (Client):** Uses socketio.client, engineio.client (network communication to Pi)
- **Epic 8 (Standalone):** REMOVES client packages, ADDS server packages (Flask, OpenCV, MediaPipe)
- **Critical Changes:**
  - flask_talisman: REQUIRED (unconditional import app/__init__.py line 3)
  - flask_socketio: OPTIONAL (try/except import) - recommended to EXCLUDE for -5 MB savings
  - MediaPipe: Version 0.10.31 (x64) / 0.10.18 (ARM64) exact versions required
  - Epic 8 bundles ENTIRE backend (Flask + OpenCV + MediaPipe = +150-200 MB vs Epic 7)

### File Size Expectations

**Epic Description (OUTDATED):**
- Epic 8 spec: "~40-50 MB single .exe, bundled dependencies"
- **Reality Check:** This is INCORRECT. Epic 8 includes full backend.

**Component Breakdown (Precise Estimate):**

| Component | Size | Rationale |
|-----------|------|-----------|
| Python runtime | 30-40 MB | python313.dll + stdlib |
| Flask + Werkzeug + Jinja2 | 5-8 MB | Web framework |
| OpenCV (cv2) | 50-70 MB | Computer vision (bulk) |
| MediaPipe (0.10.31) | 25-35 MB | Pose detection + models |
| NumPy | 15-20 MB | Array processing |
| Windows packages | 3-5 MB | pystray, winotify, pywin32 |
| Application code | 2-3 MB | app.standalone, app.cv, app.api |
| Icon + assets | <1 MB | Multi-resolution icon |
| **Subtotal (uncompressed)** | **130-182 MB** | One-folder distribution |

**Compression Analysis:**

**With UPX + LZMA2 (Recommended):**
- **UPX compression:** ~25-40% reduction on Python DLLs (pre-Inno Setup)
- **LZMA2 ultra64:** ~40-50% compression (Inno Setup final installer)
- **Combined effect:** 130-182 MB → **80-120 MB installer**

**Installer Size Targets:**
- **Target:** ≤100 MB (good user experience, reasonable download)
- **Realistic Range:** 80-120 MB (with UPX + LZMA2 compression)
- **Maximum Acceptable:** ≤150 MB (enterprise threshold)

**Compare Epic 7:**
- Epic 7 client: ~60-100 MB (no backend)
- Epic 8 standalone: **80-120 MB** (backend + compression)
- **Difference:** ~20-60 MB larger (acceptable for full backend bundling)

**Source:** PyInstaller bundled package analysis, MediaPipe 0.10.31 package size, UPX + LZMA2 compression ratios

### Performance Targets

| Metric | Story 8.5 Target | Story 8.6 Additional | Validation Method |
|--------|------------------|----------------------|-------------------|
| Installer Size | N/A | 150-250 MB compressed | Measure installer .exe |
| Installed Size | N/A | 200-300 MB uncompressed | Measure dist/ folder |
| Startup Time | <5s (source) | <5s (bundled) | Stopwatch: double-click to tray icon |
| Memory | <255 MB | <255 MB (no regression) | Task Manager after 5 min |
| CPU | <35% avg | <35% avg (no regression) | Performance Monitor |
| Build Time | N/A | 2-5 minutes | Time PyInstaller execution |

**Performance Comparison:**
- Story 8.5 (source): Memory ~200-250 MB, startup ~3s
- Story 8.6 (bundled): Memory <255 MB, startup <5s (PyInstaller extraction overhead)
- Acceptable degradation: +2s startup (one-time cost on launch)

### Reusable Components from Epic 7

**Build Infrastructure (80-90% Reusable):**

**1. PyInstaller Spec (`deskpulse_client.spec`):**
- ✅ Structure (Analysis, PYZ, EXE, COLLECT)
- ✅ One-folder mode configuration
- ✅ UPX compression settings
- ✅ Icon configuration
- ✅ Console=False setting
- ❌ Entry point (change to `app/standalone/__main__.py`)
- ❌ Hidden imports (change for backend inclusion)
- ❌ Excludes list (change for backend inclusion)

**2. Build Script (`build.ps1`):**
- ✅ Prerequisites check pattern (~100%)
- ✅ Clean step pattern (~100%)
- ✅ Build execution pattern (~100%)
- ✅ Verification pattern (~90%)
- ✅ Error handling pattern (~100%)
- ❌ Spec file path (change to `standalone.spec`)
- ❌ Output directory (change to `dist/DeskPulse-Standalone`)
- ❌ Dependency list (add Flask, OpenCV, MediaPipe checks)

**3. Inno Setup Script (`installer.iss`):**
- ✅ Setup section structure (~90%)
- ✅ Files section pattern (~100%)
- ✅ Icons section pattern (~100%)
- ✅ Tasks section (auto-start) (~100%)
- ✅ Run section (post-install launch) (~100%)
- ✅ Code section (uninstall prompt) (~100%)
- ❌ App name ("DeskPulse Standalone Edition")
- ❌ Version (2.0.0)
- ❌ Source path (`dist/DeskPulse-Standalone`)

**4. Documentation (`README.md`):**
- ✅ Prerequisites section pattern (~70%)
- ✅ Quick build section pattern (~90%)
- ✅ Full build section pattern (~90%)
- ✅ Testing section pattern (~80%)
- ✅ Troubleshooting section pattern (~60%)
- ✅ Distribution section pattern (~90%)
- ❌ Performance expectations (update for larger size)
- ❌ Backend-specific troubleshooting (MediaPipe, OpenCV errors)

**Adaptation Strategy:**
1. Copy Epic 7 files as templates
2. Search-replace key identifiers (client → standalone)
3. Update entry points and paths
4. Expand hiddenimports for backend
5. Update documentation for size and performance differences
6. Test thoroughly on clean VMs

### Story 8.5 Completion Dependencies

**CRITICAL:** Story 8.6 CANNOT start until Story 8.5 is 100% complete.

**Story 8.5 Status (as of 2026-01-11):**
- ✅ **Code Complete:** 2,091 lines (477 main + 1,100 tests + 521 mods)
- ✅ **Code Review Complete:** 10/10 issues fixed (100% resolution)
- ⏳ **Windows Validation Pending:** Requires Windows 10/11 hardware
- ⏳ **30-minute Stability Test Pending:** 0 crashes, <255 MB RAM, <35% CPU

**Story 8.6 Blockers:**
- ❌ Windows 10 hardware validation incomplete
- ❌ Windows 11 hardware validation incomplete
- ❌ 30-minute stability test not run
- ❌ Story 8.5 status not "done" in sprint-status.yaml

**When to Start Story 8.6:**
1. Story 8.5 Windows validation passes (both Windows 10 and 11)
2. 30-minute stability test passes (0 crashes, memory stable)
3. Story 8.5 marked "done" in `sprint-status.yaml`
4. All Story 8.5 deliverables committed to git

**Why This Dependency Matters:**
- PyInstaller bundles the EXACT code from Story 8.5
- Any bugs in Story 8.5 will be frozen in the .exe
- Cannot iterate on bundled code without rebuilding
- Windows validation confirms code works BEFORE bundling

**Development Strategy:**
- **Option 1 (Recommended):** Wait for Story 8.5 Windows validation, then start 8.6
- **Option 2 (Parallel):** Prepare build scripts (Tasks 1-3), but DON'T build until 8.5 done
- **Option 3 (Risk):** Build with incomplete Story 8.5, expect to rebuild multiple times

### Testing Strategy

**Unit Tests:**
- None required (Story 8.6 is build/packaging only)
- All functionality tested in Story 8.5

**Integration Tests:**
- None required (PyInstaller build is integration itself)

**Manual Testing (CRITICAL):**

**Test 1: Development Machine Build**
- Prerequisites check passes
- Clean step removes previous builds
- PyInstaller build succeeds
- Executable created and runnable
- All dependencies bundled
- No ImportError on launch

**Test 2: Clean Windows 10 VM**
- Installer runs on clean VM (no Python)
- Installation completes without errors
- Application launches successfully
- All functionality works (from Story 8.5 ACs)
- Auto-start option works
- Uninstaller works (with user data prompt)
- Performance within targets

**Test 3: Clean Windows 11 VM**
- Repeat Test 2 on Windows 11
- Validate Windows 11 specific features (tray, notifications)
- Compare performance with Windows 10
- Document any OS-specific issues

**Test 4: Upgrade Path**
- Install v1.0.0 (if exists), customize config
- Install v2.0.0 over v1.0.0
- Verify config preserved
- Verify database preserved
- Verify application works

**Test 5: SmartScreen Handling**
- Run installer on VM
- Verify SmartScreen warning appears
- Follow bypass instructions
- Verify application launches
- Verify warning doesn't reappear

**Validation Deliverables:**
- `validation-report-8-6-windows10-YYYY-MM-DD.md`
- `validation-report-8-6-windows11-YYYY-MM-DD.md`
- `distribution-checklist-8-6.md`

---

### Windows VM Setup Guide (For Tasks 4-5 Enterprise Validation)

**CRITICAL:** Tasks 4-5 require clean Windows VMs with NO Python, NO dev tools. This guide provides step-by-step setup.

#### **Option 1: Hyper-V (Windows 10/11 Pro/Enterprise/Server)**

**Enable Hyper-V:**
1. Control Panel → Programs and Features → Turn Windows features on or off
2. Check "Hyper-V" (requires restart)
3. Or via PowerShell (admin): `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All`

**Download Windows ISO:**
- **Windows 10:** https://www.microsoft.com/software-download/windows10
- **Windows 11:** https://www.microsoft.com/software-download/windows11
- Select "Create installation media" → Download ISO (~5-6 GB)

**Create VM:**
1. Open Hyper-V Manager
2. New → Virtual Machine
3. **Generation:** Generation 2 (UEFI, required for Windows 11)
4. **Memory:** 4096 MB (4 GB minimum, 8 GB recommended)
5. **Networking:** Default Switch or External (for internet access)
6. **Virtual Hard Disk:** 64 GB (dynamic expansion)
7. **Installation Options:** Install from ISO file (browse to downloaded ISO)
8. Finish and Start VM

**Configure Windows:**
1. Follow installation wizard (language, keyboard, license)
2. **Account:** Use local account (skip Microsoft account for clean state)
3. **Privacy:** Disable telemetry for testing (optional)
4. **Updates:** Disable automatic updates during testing (Settings → Windows Update → Pause updates)
5. **Software:** Do NOT install Python, Visual Studio, Git, or any dev tools

---

#### **Option 2: Oracle VirtualBox (Free, Cross-Platform)**

**Download VirtualBox:**
- https://www.virtualbox.org/wiki/Downloads
- Download VirtualBox + Extension Pack (for USB 2.0/3.0 support)
- Install on host machine (Windows, macOS, Linux)

**Download Windows ISO:** (same as Hyper-V option above)

**Create VM:**
1. Open VirtualBox → New
2. **Name:** `DeskPulse-Test-Win10` (or Win11)
3. **Type:** Microsoft Windows
4. **Version:** Windows 10 (64-bit) or Windows 11 (64-bit)
5. **Memory:** 4096 MB (8192 MB recommended)
6. **Hard Disk:** Create virtual hard disk now
   - **Type:** VDI (VirtualBox Disk Image)
   - **Storage:** Dynamically allocated
   - **Size:** 64 GB
7. Click Create

**Configure VM Settings:**
1. Right-click VM → Settings
2. **System → Motherboard:**
   - Enable EFI (required for Windows 11)
   - Boot order: Optical, Hard Disk
3. **System → Processor:**
   - CPUs: 2 (enables realistic performance testing)
4. **Display:**
   - Video Memory: 128 MB
   - Graphics Controller: VBoxSVGA or VMSVGA
5. **Storage:**
   - Controller IDE → Empty → Click disk icon → Choose disk file → Select Windows ISO
6. **Network:**
   - Adapter 1: NAT or Bridged (for internet/GitHub downloads)

**Install Windows:**
1. Start VM → Windows installer boots from ISO
2. Follow same configuration as Hyper-V (local account, no dev tools)
3. After installation, install **VirtualBox Guest Additions:**
   - VM menu → Devices → Insert Guest Additions CD image
   - Run setup inside VM
   - **Benefits:** Better graphics, shared folders, drag-and-drop, clipboard sharing

---

#### **VM Requirements Summary**

| Requirement | Minimum | Recommended | Notes |
|-------------|---------|-------------|-------|
| **RAM** | 4 GB | 8 GB | More realistic for performance testing |
| **Disk** | 40 GB free | 64 GB total | Windows + installer + headroom |
| **CPU** | 2 cores | 4 cores | Enables multi-threaded testing |
| **Network** | NAT or Bridged | Bridged | For GitHub Release downloads |
| **Graphics** | 128 MB VRAM | 256 MB | For camera UI and tray icon testing |

---

#### **Transfer Installer to VM (4 Options)**

**Option A: Network Share (Hyper-V/VirtualBox)**
```powershell
# On host machine:
# Share folder containing installer
# In VM: Map network drive \\host\shared
```

**Option B: VM Guest Additions (VirtualBox)**
```
# After installing Guest Additions:
# VM menu → Devices → Drag and Drop → Bidirectional
# VM menu → Devices → Shared Clipboard → Bidirectional
# Drag installer from host to VM desktop
```

**Option C: Download from GitHub Release (Most Realistic)**
```
# In VM browser:
# Navigate to: https://github.com/EmekaOkaforTech/deskpulse/releases
# Download: DeskPulse-Standalone-Setup-v2.0.0.exe
# Tests real user download flow, validates SmartScreen handling
```

**Option D: USB Passthrough (VirtualBox/VMware)**
```
# VM menu → Devices → USB → Select USB device with installer
# Requires VirtualBox Extension Pack
```

---

#### **Verify Clean State (Run in VM PowerShell)**

**CRITICAL:** VM must have NO Python, NO dev tools before testing.

```powershell
# Verify Python NOT installed
python --version        # Should fail: "python is not recognized"
py --version           # Should fail
pip --version          # Should fail

# Verify no Python in PATH
where python           # Should return: "INFO: Could not find files"
where pip              # Should return: "INFO: Could not find files"

# Verify no dev tools
Get-Command code       # Should fail (VS Code not installed)
Get-Command devenv     # Should fail (Visual Studio not installed)
Get-Command git        # Should fail (Git not installed)

# Verify Windows version
[System.Environment]::OSVersion.Version
# Windows 10: Version 10.0.19045 (22H2) or later
# Windows 11: Version 10.0.22621 (22H2) or later

# Verify architecture
[System.Environment]::Is64BitOperatingSystem  # Should return: True
```

**If ANY of these commands succeed, VM is NOT clean state!**

---

#### **VM Snapshot Best Practice**

**CRITICAL:** Take snapshots to enable fast test iteration without VM rebuild.

**Hyper-V Snapshots:**
1. Hyper-V Manager → Select VM → Checkpoint (Ctrl+Shift+C)
2. Name: "Clean-Windows10-22H2-NoDevTools-PreInstaller"
3. To revert: Right-click snapshot → Apply

**VirtualBox Snapshots:**
1. VM powered off or running
2. Machine → Take Snapshot (Ctrl+Shift+T)
3. Name: "Clean-Windows10-22H2-NoDevTools-PreInstaller"
4. Description: "Clean state verified, ready for DeskPulse installer test"
5. To revert: Machine → Restore Snapshot

**Snapshot Strategy:**
- **Snapshot 1:** "Clean Windows installed, updates paused, no software"
- **Snapshot 2:** "After first installer test (for upgrade path testing)"
- **Snapshot 3:** "After uninstaller test (for clean install re-test)"

**Benefits:**
- Revert to clean state in 30 seconds vs 30 minutes rebuild
- Consistent test environment every iteration
- Enable rapid testing of installer changes

---

### Git Intelligence (Recent Patterns)

**Story Completion Patterns:**
- Story 8.5: "CODE COMPLETE 2026-01-11", "CODE REVIEW DONE", "Awaiting Windows validation"
- Story 8.4: "DONE - Local IPC architecture complete" (70/70 tests passing)
- Story 8.3: "DONE - Windows camera capture complete" (99/99 tests passing)
- Story 8.2: "100% ENTERPRISE VALIDATION - Real Hardware Testing Complete"

**Follow the Same Pattern for Story 8.6:**
1. **Code Complete:** All build scripts written, tested on development machine
2. **Code Review:** Self-review build scripts for errors, test on clean environment
3. **Windows Validation:** Test on actual Windows 10/11 VMs
4. **Performance Validation:** Measure installer size, startup time, memory usage
5. **Documentation Complete:** README, troubleshooting, distribution checklist
6. **Distribution Package:** GitHub Release with installer, checksum, release notes

**Commit Message Pattern:**
```
Story 8.6: DONE - All-in-one installer complete

- PyInstaller spec: build/windows/standalone.spec
- Build script: build/windows/build_standalone.ps1
- Inno Setup: build/windows/installer_standalone.iss
- Installer: DeskPulse-Standalone-Setup-v2.0.0.exe (XXX MB)
- Tested: Windows 10 + Windows 11 VMs (clean installs)
- Performance: Startup <5s, Memory <255 MB, 0 crashes
- Distribution: GitHub Release v2.0.0-standalone

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Related Documents

- **Epic 8:** `/home/dev/deskpulse/docs/sprint-artifacts/epic-8-standalone-windows.md`
- **Story 8.1:** `/home/dev/deskpulse/docs/sprint-artifacts/8-1-windows-backend-port.md`
- **Story 8.2:** `/home/dev/deskpulse/docs/sprint-artifacts/8-2-mediapipe-tasks-api-migration.md`
- **Story 8.3:** `/home/dev/deskpulse/docs/sprint-artifacts/8-3-windows-camera-capture.md`
- **Story 8.4:** `/home/dev/deskpulse/docs/sprint-artifacts/8-4-local-architecture-ipc.md`
- **Story 8.5:** `/home/dev/deskpulse/docs/sprint-artifacts/8-5-unified-system-tray-application.md` (DEPENDENCY)
- **Epic 7 Story 7.5:** `/home/dev/deskpulse/docs/sprint-artifacts/7-5-windows-installer-with-pyinstaller.md` (PATTERN)
- **Build README:** `/home/dev/deskpulse/build/windows/README.md` (Epic 7 pattern)

---

## Dev Agent Record

### Context Reference

Story context created by SM agent (Bob) in YOLO mode with comprehensive codebase analysis, Story 8.5 dependency analysis, Epic 7 build pattern analysis, and enterprise requirements integration.

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

None - story created in draft mode

### Completion Notes List

**Pre-Implementation (SM Agent - Story Creation):**
- ✅ Comprehensive codebase analysis via direct file reads
- ✅ Story 8.5 deliverables analyzed (__main__.py, tray_app.py, backend_thread.py)
- ✅ Epic 7 build patterns analyzed (deskpulse_client.spec, build.ps1, installer.iss)
- ✅ Dependency analysis (requirements.txt + requirements-windows.txt)
- ✅ Hidden imports analysis (Epic 7 vs Epic 8 differences)
- ✅ File size expectations calculated (200-300 MB realistic vs epic's 40-50 MB)
- ✅ Integration points identified (entry point, spec changes, build script adaptation)
- ✅ Enterprise requirements documented (no mocks, real testing, comprehensive docs)
- ✅ Performance targets defined (installer size, startup time, memory)
- ✅ Comprehensive acceptance criteria (8 ACs) and tasks (7 tasks, 50+ subtasks) created

**Implementation (Dev Agent - 2026-01-11):**
- ✅ Task 1: PyInstaller spec file created (183 lines)
- ✅ Task 2: Build automation script created (493 lines)
- ✅ Task 3: Inno Setup installer script created (154 lines)
- ✅ Task 6: Build documentation created (685 lines)
- ✅ Validation templates created (3 files, 1,655 lines total)
- ⏳ Task 4: Windows 10 VM testing (requires Windows hardware)
- ⏳ Task 5: Windows 11 VM testing (requires Windows hardware)
- ⏳ Task 7: GitHub Release distribution (after Windows validation)

**Build Infrastructure Details:**
- `standalone.spec`: Entry point app/standalone/__main__.py, backend bundled (Flask+OpenCV+MediaPipe), Windows integration (pystray+winotify+pywin32), one-folder mode with UPX compression, excludes socketio.client (uses server not client)
- `build_standalone.ps1`: PowerShell execution policy check, Story 8.5 verification, backend dependency validation, Epic 7 hook conflict handling (auto-rename/restore), build verification with backend DLL checks, comprehensive error handling
- `installer_standalone.iss`: Inno Setup for v2.0.0, auto-start option (unchecked default), user data preservation prompt (config+database+logs), LZMA2 ultra64 compression for 150-250 MB installer
- `README_STANDALONE.md`: Prerequisites, build instructions (quick + full), testing procedures, troubleshooting (build+runtime errors), distribution checklist, performance expectations, code signing considerations
- Validation templates: Windows 10 template (570 lines, 12 test sections), Windows 11 template (638 lines, 13 test sections with Windows 11-specific features), distribution checklist (447 lines, 11 phases)

**Total Deliverables**: 7 files created, 3,170 lines total

**Critical Intelligence Gathered:**
1. **Entry Point:** `app/standalone/__main__.py` (Story 8.5, 477 lines)
2. **Epic 7 Patterns:** 80-90% reusable, adapt for backend inclusion
3. **Hidden Imports:** REMOVE socketio.client, ADD Flask/OpenCV/MediaPipe
4. **Size Reality:** 200-300 MB (NOT 40-50 MB as epic suggests)
5. **Dependencies:** Story 8.5 MUST be complete before building
6. **Testing:** Windows 10 + Windows 11 VMs required (no mocks, real hardware)

**Implementation Decisions:**
1. **Spec File:** Adapt Epic 7 `deskpulse_client.spec`, change entry point and hiddenimports
2. **Build Script:** Adapt Epic 7 `build.ps1`, add backend dependency checks
3. **Installer:** Adapt Epic 7 `installer.iss`, update app name and version
4. **Documentation:** Create `README_STANDALONE.md` with backend-specific guidance
5. **File Structure:** `build/windows/standalone.spec`, `build_standalone.ps1`, `installer_standalone.iss`
6. **One-Folder Mode:** Keep Epic 7 pattern (faster startup, fewer AV issues)
7. **Auto-Start:** Startup folder shortcut (simple, reliable, no registry)
8. **Uninstaller:** User data preservation prompt (from Epic 7 pattern)
9. **Icon:** Reuse `assets/windows/icon_professional.ico` (exists from Epic 7)
10. **Version:** 2.0.0 (distinguishes from Epic 7 v1.0.0)

### File List

**Files Created (NEW - 2026-01-11):**
- ✅ `build/windows/standalone.spec` (183 lines) - PyInstaller configuration for Standalone Edition
- ✅ `build/windows/build_standalone.ps1` (493 lines) - Build automation with Epic 7 hook handling
- ✅ `build/windows/installer_standalone.iss` (154 lines) - Inno Setup configuration for v2.0.0
- ✅ `build/windows/README_STANDALONE.md` (685 lines) - Comprehensive build documentation
- ✅ `docs/sprint-artifacts/validation-report-8-6-windows10-template.md` (570 lines) - Windows 10 test template
- ✅ `docs/sprint-artifacts/validation-report-8-6-windows11-template.md` (638 lines) - Windows 11 test template
- ✅ `docs/sprint-artifacts/distribution-checklist-8-6.md` (447 lines) - Distribution checklist template
- ⏳ `docs/sprint-artifacts/validation-report-8-6-windows10-2026-01-XX.md` - Actual Windows 10 test report (after testing)
- ⏳ `docs/sprint-artifacts/validation-report-8-6-windows11-2026-01-XX.md` - Actual Windows 11 test report (after testing)
- ⏳ `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe` - Final installer (after Windows build)
- ⏳ `build/windows/Output/SHA256SUMS.txt` - Checksum file (after Windows build)
- ⏳ `build/windows/build_standalone.log` - Build log (generated during build)

**Files to Modify (Pending Windows Validation):**
- ⏳ `README.md` - Add Windows Standalone Edition section (after release)
- ⏳ `CHANGELOG.md` - Add v2.0.0 release notes (after release)
- ✅ `docs/sprint-artifacts/sprint-status.yaml` - Updated to "in-progress"
- ✅ `docs/sprint-artifacts/8-6-all-in-one-installer.md` (this file) - Updated with implementation notes

**Files to Reuse (Epic 7 - NO CHANGES):**
- ✅ `assets/windows/icon_professional.ico` - Multi-resolution icon (exists)
- ✅ `build/windows/deskpulse_client.spec` - Pattern reference (Epic 7)
- ✅ `build/windows/build.ps1` - Pattern reference (Epic 7)
- ✅ `build/windows/installer.iss` - Pattern reference (Epic 7)
- ✅ `build/windows/README.md` - Pattern reference (Epic 7)

---

## Status

**Current Status:** Drafted

**Story Created:** 2026-01-11
**Story Created By:** SM Agent (Bob) - BMAD Method
**Awaiting:** Story 8.5 completion (Windows 10/11 validation)

**Blockers:**
- Story 8.5 Windows hardware validation incomplete
- Story 8.5 30-minute stability test pending
- Story 8.5 not marked "done" in sprint-status.yaml

**Ready Criteria:**
- Story 8.5 status = "done"
- All Story 8.5 deliverables committed
- Windows 10/11 PC or VM available for testing

**Next Steps:**
1. ⏳ Wait for Story 8.5 completion
2. ⏳ Prepare Windows 10/11 test VMs
3. ⏳ Start Task 1 (Create PyInstaller spec)
4. ⏳ Execute Tasks 2-7 sequentially
5. ⏳ Mark story complete after distribution package ready

---

**End of Story 8.6: All-in-One Installer**
