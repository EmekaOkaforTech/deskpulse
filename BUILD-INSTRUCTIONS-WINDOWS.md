# DeskPulse Standalone Windows Build Instructions

**Story 8.6 - Professional Installer Creation**

This guide walks through creating the final Windows installer for DeskPulse Standalone Edition v2.0.0.

---

## Prerequisites

### Required Software:
1. **Python 3.9+ (64-bit)** - https://www.python.org/downloads/
2. **Git for Windows** - https://git-scm.com/download/win
3. **Inno Setup 6** - https://jrsoftware.org/isinfo.php
4. **PowerShell 5.1+** - Pre-installed on Windows 10/11

### Verify Installation:
```powershell
# Check Python (must be 64-bit, 3.9+)
python --version
python -c "import platform; print(platform.architecture()[0])"

# Check Git
git --version

# Check Inno Setup (if installed to default location)
Test-Path "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

---

## Step 1: Pull Latest Code (Enterprise-Grade Fixes)

All enterprise-grade fixes have been pushed to the repository:

```powershell
# Navigate to your project directory
cd C:\path\to\deskpulse

# Pull latest changes
git pull origin master
```

**What's New (Commit: 3d79034):**
- ✅ Fixed dialog box deadlock (all dialogs now close properly)
- ✅ Enterprise-grade dialog layouts (Stats, History, Settings, About)
- ✅ Professional icon loading system
- ✅ New menu items: "Open Dashboard" and "View Logs"
- ✅ Camera preview close error fixed
- ✅ Complete STORY-8-5-FEATURE-AUDIT.md documentation

---

## Step 2: Install Python Dependencies

```powershell
# Install/update all dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-windows.txt

# Verify critical packages
pip show pyinstaller flask opencv-python mediapipe pystray winotify pywin32
```

**Expected Versions:**
- PyInstaller: 6.0+
- Flask: 3.0+
- opencv-python: 4.8+
- mediapipe: 0.10.31
- pystray: 0.19+
- winotify: 1.1+

---

## Step 3: Build PyInstaller Executable

This creates the standalone executable with full backend bundled.

```powershell
# Run automated build script (recommended)
.\build\windows\build_standalone.ps1

# Expected output:
# - dist/DeskPulse-Standalone/DeskPulse.exe
# - Distribution size: 200-300 MB
# - Build time: 3-7 minutes
```

**What the Script Does:**
1. Validates prerequisites (Python, PyInstaller, icon file)
2. Checks backend dependencies (Flask, OpenCV, MediaPipe)
3. Handles PyInstaller hook conflicts
4. Cleans previous builds
5. Runs PyInstaller with standalone.spec
6. Verifies build output (including backend DLLs)
7. Reports build metrics

**If Build Fails:**
- Check build log: `build/windows/build_standalone.log`
- Common issues:
  - Missing dependencies: Run `pip install -r requirements.txt requirements-windows.txt`
  - Icon missing: Verify `assets/windows/icon_professional.ico` exists
  - Import errors: Check hiddenimports in `build/windows/standalone.spec`

---

## Step 4: Test Standalone Executable

Before creating the installer, verify the executable works:

```powershell
# Run standalone executable
.\dist\DeskPulse-Standalone\DeskPulse.exe
```

**Validation Checklist:**
- [x] System tray icon appears (colored circle)
- [x] Right-click menu shows all items:
  - Pause/Resume Monitoring
  - View Camera Feed
  - Today's Stats
  - 7-Day History
  - Open Dashboard
  - Settings
  - View Logs
  - About
  - Quit DeskPulse
- [x] All dialogs open and close properly (OK/X buttons work)
- [x] Toast notifications appear for alerts
- [x] Camera preview window opens and closes without errors
- [x] Web dashboard opens at http://localhost:5000
- [x] Logs directory opens in Explorer

**If Errors Occur:**
- Check console output for errors
- Verify %APPDATA%\DeskPulse\ directory created
- Check logs in %APPDATA%\DeskPulse\logs\

**Close the executable before proceeding to installer build.**

---

## Step 5: Build Inno Setup Installer

This creates the professional Windows installer.

### 5A. Manual Build (Recommended):

```powershell
# Build installer with Inno Setup
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
```

**Expected Output:**
- File: `build/windows/Output/DeskPulse-Standalone-Setup-v2.0.0.exe`
- Size: 150-250 MB (compressed with LZMA2 ultra64)
- Build time: 2-5 minutes

### 5B. Automated Build Script (Alternative):

```powershell
# Create installer build script (if not exists)
# This is an alternative to manual ISCC.exe invocation

.\build\windows\build_installer_standalone.ps1
```

---

## Step 6: Verify Installer

Check the installer was created successfully:

```powershell
# Check installer exists
Test-Path "build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe"

# Get installer size
$installer = Get-Item "build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe"
$sizeMB = [math]::Round($installer.Length / 1MB, 1)
Write-Host "Installer size: $sizeMB MB"

# Expected: 150-250 MB
```

---

## Step 7: Test Installer on Clean VM (CRITICAL)

Testing on a clean Windows VM ensures the installer works for end users who don't have Python or development tools.

### Setup Clean VM:
1. Download Windows 10/11 ISO from Microsoft
2. Create VM in VirtualBox/VMware/Hyper-V
3. Install Windows (no additional software)
4. Copy `DeskPulse-Standalone-Setup-v2.0.0.exe` to VM

### Test Installation:
```
1. Double-click DeskPulse-Standalone-Setup-v2.0.0.exe
2. Follow installation wizard:
   - Accept license
   - Choose installation directory (default: C:\Program Files\DeskPulse)
   - [Optional] Check "Start DeskPulse automatically when Windows starts"
   - Install

3. Verify installation:
   - Start Menu → DeskPulse shortcut exists
   - DeskPulse launches without errors
   - No console window appears (windowed mode)
   - System tray icon appears
   - All menu items work (use validation checklist from Step 4)

4. Test auto-start (if enabled):
   - Restart Windows
   - DeskPulse should start automatically
   - System tray icon appears within 30 seconds

5. Test uninstaller:
   - Windows Settings → Apps → DeskPulse → Uninstall
   - Choose whether to keep or delete user data (%APPDATA%\DeskPulse)
   - Verify clean uninstallation
```

**Windows SmartScreen Warning:**
- On first run, Windows may show "Windows protected your PC"
- This is normal for unsigned executables
- Click "More info" → "Run anyway"
- To avoid: Code-sign the installer (requires certificate, optional)

---

## Step 8: Generate Release Artifacts

### 8A. Calculate SHA256 Checksums:

```powershell
# Generate SHA256 for installer
$installer = "build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe"
$hash = Get-FileHash -Path $installer -Algorithm SHA256
Write-Host "SHA256: $($hash.Hash)"

# Save to file
$hash.Hash | Out-File "build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe.sha256"
```

### 8B. Create Release Notes:

Create `RELEASE-NOTES-v2.0.0.md`:

```markdown
# DeskPulse v2.0.0 - Standalone Windows Edition

**Release Date:** January 13, 2026

## Overview
First commercial-ready release of DeskPulse Standalone Edition for Windows 10/11.

## Features
- ✅ Real-time posture monitoring using webcam
- ✅ System tray integration with toast notifications
- ✅ Today's stats and 7-day history tracking
- ✅ Web dashboard for detailed analytics
- ✅ Camera preview for validation
- ✅ Auto-start with Windows (optional)
- ✅ No Python or dependencies required
- ✅ Professional Windows installer

## Installation
1. Download `DeskPulse-Standalone-Setup-v2.0.0.exe`
2. Verify SHA256: [checksum]
3. Double-click to install
4. Follow installation wizard
5. Launch from Start Menu

## System Requirements
- Windows 10 (64-bit) or Windows 11
- Webcam (built-in or USB)
- 500 MB disk space
- 4 GB RAM minimum

## Known Issues
- Windows SmartScreen warning on first run (unsigned installer)
- Some antivirus software may require approval (false positive)

## Support
- Documentation: https://github.com/EmekaOkaforTech/deskpulse/wiki
- Issues: https://github.com/EmekaOkaforTech/deskpulse/issues
```

---

## Step 9: Create GitHub Release

### 9A. Tag Release:

```powershell
# Create and push tag
git tag -a v2.0.0 -m "Release v2.0.0 - Standalone Windows Edition"
git push origin v2.0.0
```

### 9B. Upload to GitHub:

1. Go to https://github.com/EmekaOkaforTech/deskpulse/releases
2. Click "Draft a new release"
3. Select tag: v2.0.0
4. Title: "DeskPulse v2.0.0 - Standalone Windows Edition"
5. Upload files:
   - `DeskPulse-Standalone-Setup-v2.0.0.exe`
   - `DeskPulse-Standalone-Setup-v2.0.0.exe.sha256`
6. Paste release notes
7. Check "Set as the latest release"
8. Publish release

---

## Troubleshooting

### Build Issues:

**PyInstaller fails with import errors:**
```powershell
# Add missing module to standalone.spec hiddenimports
# Example: 'mediapipe.python.solutions'
```

**Executable size too small (<150 MB):**
- Backend components missing
- Check build log: `build/windows/build_standalone.log`
- Verify all dependencies installed

**Icon errors:**
```powershell
# Verify icon exists
Test-Path "assets\windows\icon_professional.ico"
```

### Runtime Issues:

**Console errors about missing DLLs:**
- Reinstall dependencies: `pip install -r requirements-windows.txt`
- Rebuild with PyInstaller

**Camera not detected:**
- Check Windows Camera Privacy Settings
- Verify camera works in Camera app
- Check device manager for driver issues

**Toast notifications don't appear:**
- Verify Windows notifications enabled
- Check Focus Assist settings

### Installer Issues:

**Inno Setup not found:**
```powershell
# Download and install from:
# https://jrsoftware.org/isinfo.php

# Default location should be:
# C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

**Installer creation fails:**
- Verify PyInstaller build completed: `dist/DeskPulse-Standalone/DeskPulse.exe`
- Check Inno Setup log for errors
- Verify icon file exists

---

## Build Metrics Reference

### Expected Sizes:
- **PyInstaller Executable:** ~50 MB
- **Full Distribution (one-folder):** 200-300 MB
- **Installer (compressed):** 150-250 MB

### Expected Build Times:
- **PyInstaller Build:** 3-7 minutes
- **Inno Setup Installer:** 2-5 minutes
- **Total Build Time:** 5-12 minutes

### File Counts:
- **Distribution Files:** ~1,500-2,000 files
- **Installer Files:** 1 executable

---

## Next Steps After Release

1. **Beta Testing:**
   - Distribute to 5-10 beta testers
   - Gather feedback on installation and usage
   - Monitor for crashes or errors

2. **Documentation:**
   - Create user manual
   - Record demo video
   - Write installation guide for less technical users

3. **Marketing:**
   - Announce on GitHub
   - Post on relevant forums/communities
   - Create product landing page

4. **Future Enhancements (Epic 9):**
   - 30+ day history tracking
   - Pain tracking integration
   - Pattern detection
   - Export and reporting features

---

## Summary

You've now completed Story 8.6 and Epic 8! You have:

✅ Enterprise-grade Windows application
✅ Professional installer for end users
✅ Tested on clean Windows VM
✅ Ready for public distribution
✅ Commercial-ready product

**Congratulations!** DeskPulse Standalone Edition is ready for launch! 🚀
