# DeskPulse Windows Standalone Build Process

## Overview
This document defines the EXACT build process for creating the Windows installer.
**Claude must reference this document before providing build commands.**

## Directory Structure

### Linux (Source)
```
/home/dev/deskpulse/
├── app/                          # Application code
├── assets/windows/               # Icons
├── build/windows/
│   ├── standalone.spec           # PyInstaller spec (paths relative to HERE)
│   ├── installer_standalone.iss  # Inno Setup script
│   └── BUILD-PROCESS.md          # This file
```

### Windows (Build Machine)
```
C:\deskpulse-build\deskpulse_installer\
├── app\                          # Application code (from Linux)
├── assets\windows\               # Icons (from Linux)
├── build\windows\
│   ├── standalone.spec           # PyInstaller spec
│   ├── installer_standalone.iss  # Inno Setup script
│   └── Output\                   # Installer output (created by Inno Setup)
├── dist\
│   └── DeskPulse-Standalone\     # PyInstaller output (MUST BE HERE for .iss)
└── venv\                         # Python virtual environment
```

## Build Steps

### Step 1: Transfer Updated Files from Linux
Run on Windows PowerShell:
```powershell
cd C:\deskpulse-build\deskpulse_installer

# Transfer specific updated files (example - adjust based on what changed)
scp dev@192.168.10.133:/home/dev/deskpulse/app/standalone/tray_app.py app\standalone\
scp dev@192.168.10.133:/home/dev/deskpulse/app/standalone/backend_thread.py app\standalone\
scp dev@192.168.10.133:/home/dev/deskpulse/app/standalone/camera_windows.py app\standalone\
scp dev@192.168.10.133:/home/dev/deskpulse/build/windows/standalone.spec build\windows\
scp dev@192.168.10.133:/home/dev/deskpulse/build/windows/installer_standalone.iss build\windows\
```

### Step 2: Clean Previous Build
```powershell
cd C:\deskpulse-build\deskpulse_installer
Remove-Item -Recurse -Force dist\DeskPulse-Standalone -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build\windows\dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force build\windows\build -ErrorAction SilentlyContinue
```

### Step 3: Run PyInstaller (from build\windows directory)
**CRITICAL: Must run from build\windows because standalone.spec uses relative paths like ../../app**
```powershell
cd C:\deskpulse-build\deskpulse_installer\build\windows
pyinstaller standalone.spec --clean --noconfirm
```
Output goes to: `build\windows\dist\DeskPulse-Standalone\`

### Step 4: Move Build Output to Expected Location
**CRITICAL: The .iss file expects files at dist\DeskPulse-Standalone\ (relative to root)**
```powershell
cd C:\deskpulse-build\deskpulse_installer
Move-Item -Force build\windows\dist\DeskPulse-Standalone dist\
```

### Step 5: Run Inno Setup (from root directory)
```powershell
cd C:\deskpulse-build\deskpulse_installer
& "C:\Users\okafor_dev\AppData\Local\Programs\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
```
Output: `build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe`

## Complete One-Liner (After File Transfer)
```powershell
cd C:\deskpulse-build\deskpulse_installer; Remove-Item -Recurse -Force dist\DeskPulse-Standalone -ErrorAction SilentlyContinue; Remove-Item -Recurse -Force build\windows\dist -ErrorAction SilentlyContinue; cd build\windows; pyinstaller standalone.spec --clean --noconfirm; cd ..\.. ; Move-Item -Force build\windows\dist\DeskPulse-Standalone dist\; & "C:\Users\okafor_dev\AppData\Local\Programs\Inno Setup 6\ISCC.exe" build\windows\installer_standalone.iss
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `script 'C:\app\standalone\__main__.py' not found` | Running PyInstaller from wrong directory | Run from `build\windows\` |
| `No files found matching "..\..\dist\DeskPulse-Standalone\*"` | Build output not moved | Move `build\windows\dist\DeskPulse-Standalone` to `dist\` |
| `No module named 'tkinter'` | Missing from hiddenimports | Add tkinter to standalone.spec |
| Inno Setup path error for icon | Wrong relative path | Icon path: `..\..\assets\windows\icon_professional.ico` |

## File Locations After Successful Build
- Installer: `C:\deskpulse-build\deskpulse_installer\build\windows\Output\DeskPulse-Standalone-Setup-v2.0.0.exe`
- Size: ~65-70 MB (compressed)

## Version History
- 2026-01-14: Initial documentation created after multiple build issues
