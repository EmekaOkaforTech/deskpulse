# DeskPulse Windows Build System

Enterprise-grade Windows installer build system using **PyInstaller** + **Inno Setup**.

Produces:
- **Standalone executable**: `dist/DeskPulse/DeskPulse.exe` (one-folder distribution)
- **Windows installer**: `build/windows/Output/DeskPulse-Setup-v1.0.0.exe`

---

## Prerequisites

### Required Software

1. **Operating System**
   - Windows 10 1803+ or Windows 11 (64-bit)
   - Required for: toast notifications, testing

2. **Python 3.9+ (64-bit)**
   - Download: https://www.python.org/downloads/
   - Verify: `python --version` (must show Python 3.9.x or higher)
   - Verify 64-bit: `python -c "import platform; print(platform.architecture()[0])"`
   - Must output: `64bit`

3. **PyInstaller 6.0+**
   - Install: `pip install pyinstaller`
   - Verify: `pip show pyinstaller`
   - Auto-installed by build script if missing

4. **Inno Setup 6** (optional, for installer only)
   - Download: https://jrsoftware.org/isdl.php
   - Required only if creating installer (not needed for standalone .exe)

5. **Project Dependencies**
   - Install: `pip install -r requirements.txt`
   - Includes: pystray, winotify, socketio, requests, pywin32

### Required Files

- **Icon file**: `assets/windows/icon.ico`
  - If missing: `python assets/windows/generate_icon.py`

---

## Quick Build (Standalone .exe only)

From project root:

```powershell
.\build\windows\build.ps1
```

**Output**: `dist/DeskPulse/DeskPulse.exe`

**Build time**: 2-5 minutes
**Distribution size**: ~60-100 MB

---

## Full Build (Windows Installer)

### Step 1: Build Executable

```powershell
.\build\windows\build.ps1
```

### Step 2: Create Installer

```powershell
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" build\windows\installer.iss
```

**Output**: `build/windows/Output/DeskPulse-Setup-v1.0.0.exe`
**Installer size**: ~25-35 MB
**Build time**: ~30 seconds (after step 1)

---

## Testing Instructions

### Test 1: Standalone Executable (Development Machine)

1. Run the executable:
   ```powershell
   .\dist\DeskPulse\DeskPulse.exe
   ```

2. Verify:
   - System tray icon appears (green DeskPulse icon)
   - No console window appears
   - Backend connection attempt (requires Pi on same network)
   - Config created: `%APPDATA%\DeskPulse\config.json`
   - Logs created: `%APPDATA%\DeskPulse\logs\client.log`

3. Test functionality:
   - Right-click tray icon → Check menu items
   - "Pause Monitoring" → Icon turns gray
   - "Resume Monitoring" → Icon turns green
   - "View Stats → Today's Stats" → MessageBox displays
   - "Exit" → Application closes cleanly

### Test 2: Standalone Executable (Clean Windows VM)

**Purpose**: Verify no Python dependencies required

1. Copy `dist/DeskPulse/` folder to VM (no Python installed)
2. Run `DeskPulse.exe`
3. Verify all functionality works
4. Test backend connection (Pi must be on network)
5. Verify error handling (disconnect Pi, check error messages)

**Expected startup time**: < 5 seconds (cold start)

### Test 3: Windows Installer

1. Run `DeskPulse-Setup-v1.0.0.exe`
2. Verify:
   - Installation wizard appears (modern style)
   - Auto-start checkbox available (unchecked by default)
   - Installation to: `C:\Program Files\DeskPulse\`
   - Start Menu shortcut created
   - Post-install launch works

3. Launch from Start Menu
4. Test all functionality

5. Test auto-start:
   - Uninstall DeskPulse
   - Reinstall with "Start DeskPulse automatically" checked
   - Reboot system
   - Verify DeskPulse starts automatically (tray icon appears)

### Test 4: Uninstaller

1. Run uninstaller from: `Control Panel → Programs → DeskPulse`
2. Verify:
   - User data preservation prompt appears
   - "Delete config and logs?" dialog displays location
   - Test "No" → Config and logs preserved at `%APPDATA%\DeskPulse`
   - Reinstall, uninstall again
   - Test "Yes" → Config and logs deleted
   - Program Files directory removed
   - Start Menu shortcuts removed

### Test 5: Upgrade Path

1. Install DeskPulse v1.0.0
2. Run application, customize config:
   ```json
   {
     "backend_url": "http://192.168.1.100:5000"
   }
   ```
3. Build v1.0.1 installer (simulate version bump)
4. Install v1.0.1 over existing v1.0.0
5. Verify:
   - Config preserved (custom backend URL still set)
   - Logs preserved (previous log files still exist)
   - Application launches successfully
   - Connection to custom backend works

**Expected behavior**: Installer does NOT overwrite user config during upgrades

---

## Troubleshooting

### Build Errors

#### "PyInstaller not found"
```powershell
pip install pyinstaller
```

#### "Icon file not found: assets/windows/icon.ico"
```powershell
python assets/windows/generate_icon.py
```

#### "ModuleNotFoundError at runtime"
**Symptom**: Application crashes on launch with ImportError

**Diagnosis**:
```powershell
# Build with import debugging
pyinstaller --debug=imports build\windows\deskpulse.spec

# Run bundled .exe
.\dist\DeskPulse\DeskPulse.exe

# Check logs for ImportError
type %APPDATA%\DeskPulse\logs\client.log | findstr ImportError
```

**Solution**: Add missing module to `hiddenimports` in `build/windows/deskpulse.spec`

#### "Application doesn't start (no window, no tray icon)"
**Check logs**: `%APPDATA%\DeskPulse\logs\client.log`

**Common causes**:
- Missing hiddenimports (pystray._win32, winotify.audio, socketio.client)
- pywin32 DLL not bundled
- Icon file not bundled in assets/

**Solution**: Review spec file `datas` and `hiddenimports` sections

### Installer Errors

#### "Inno Setup not found"
Download from: https://jrsoftware.org/isdl.php

**Alternative**: Use standalone .exe without installer

#### "Source file not found: dist\DeskPulse\*"
Run PyInstaller build first:
```powershell
.\build\windows\build.ps1
```

### Runtime Errors

#### "Failed to connect to backend"
**Check**:
- Is Pi backend running? `ssh pi@raspberrypi.local "systemctl status deskpulse"`
- Is Windows client on same network as Pi?
- Can you ping raspberrypi.local? `ping raspberrypi.local`

**Solution**: Edit config.json with correct backend URL:
```json
{
  "backend_url": "http://192.168.1.100:5000"
}
```

#### "Config file permission denied"
**Cause**: Corporate IT locked down `%APPDATA%`

**Solution**: Config.py has fallback to `%TEMP%` (automatic, no action required)

#### "SmartScreen warning won't bypass"
**Symptom**: "Run anyway" button not appearing

**Cause**: Corporate IT policy blocking unsigned software

**Solutions**:
1. Request IT to whitelist DeskPulse
2. Build and run from source: `python -m app.windows_client`
3. (Future) Code signing certificate

---

## Distribution

### GitHub Releases

1. Create release tag: `v1.0.0-windows`
2. Upload: `DeskPulse-Setup-v1.0.0.exe`
3. Calculate SHA256 checksum:
   ```powershell
   certutil -hashfile build\windows\Output\DeskPulse-Setup-v1.0.0.exe SHA256
   ```
4. Add checksum to release notes
5. Document SmartScreen bypass instructions
6. Link to build documentation (this file)

### Release Notes Template

```markdown
# DeskPulse v1.0.0 - Windows Desktop Client

## Downloads
- **Windows Installer (64-bit)**: [DeskPulse-Setup-v1.0.0.exe](link)
  - Size: ~30 MB
  - SHA256: `[checksum]`

## Installation
1. Download DeskPulse-Setup-v1.0.0.exe
2. Run installer (SmartScreen warning - click "More info" → "Run anyway")
3. Follow installation wizard
4. Launch DeskPulse from Start Menu

## Requirements
- Windows 10/11 (64-bit)
- Raspberry Pi with DeskPulse backend on same network
- No Python installation required

## SmartScreen Warning
Windows SmartScreen may warn about this application because it's not code-signed.
This is normal for open-source software. You can verify the source code on GitHub before installing.

## Support
- Report issues: [GitHub Issues](link)
- Documentation: [README.md](link)
```

---

## Code Signing Considerations

### Current Status

DeskPulse Windows client is **NOT code-signed** (open-source project).

**User impact**:
- Windows SmartScreen warning on first run
- Warning: "Windows protected your PC - Microsoft Defender SmartScreen prevented an unrecognized app from starting"

**This is EXPECTED and NORMAL for unsigned open-source software.**

### SmartScreen Bypass Instructions (for users)

```
When you first run DeskPulse, Windows may show a SmartScreen warning.

To proceed:
1. Click "More info"
2. Click "Run anyway"
3. This warning won't appear again

Why unsigned?
Code signing certificates cost $200-500/year from trusted CAs.
As an open-source project, we prioritize code transparency over certificates.
You can verify our code at:
http://192.168.10.126:2221/Emeka/deskpulse
```

### Future Code Signing (Optional Enhancement)

**Cost**: $200-500/year (DigiCert, Sectigo, GlobalSign)

**Process**:
1. Purchase certificate
2. Sign .exe:
   ```powershell
   signtool.exe sign /f cert.pfx /p password /t http://timestamp.digicert.com dist\DeskPulse\DeskPulse.exe
   ```
3. Sign installer: Configure Inno Setup `SignTool`
   ```ini
   [Setup]
   SignTool=signtool sign /f cert.pfx /p password $f
   ```

**Benefits**:
- No SmartScreen warnings
- Increased user trust
- Fewer antivirus false positives
- Microsoft Defender SmartScreen reputation builds over time

---

## Performance Expectations

### Startup Performance
- **Cold start** (first run): < 5 seconds (one-folder mode)
- **Warm start** (subsequent runs): < 2 seconds
- **Comparison**: --onefile mode would be ~10-15 seconds (temp extraction)

### Resource Usage
- **Disk space**: 60-100 MB installed (one-folder mode)
- **Memory footprint**: ~50-80 MB running (same as source)
- **CPU usage**: <1% idle, ~5-10% during SocketIO events
- **Network**: Only local network traffic to Pi backend

### Bundle Size Optimization
- Excludes backend-only packages (Flask, OpenCV, MediaPipe)
- UPX compression: Reduces .exe size by 25-40%
- No bundling of development/test dependencies

---

## Architecture Notes

### Why One-Folder Mode?

**Advantages over --onefile mode**:
- ✅ **Faster startup**: No temp extraction (~3-5s vs ~10-15s)
- ✅ **Fewer antivirus false positives**: Transparent to scanners
- ✅ **Easier debugging**: Can inspect bundled files
- ✅ **Better for enterprise IT**: Predictable deployment

**Source**: [PyInstaller Operating Mode Documentation](https://pyinstaller.org/en/stable/operating-mode.html)

### Antivirus Considerations

- One-folder mode: **Fewer false positives** than one-file mode
- UPX compression: May trigger some heuristics (acceptable trade-off for size)
- Code signing: Significantly reduces false positives

**Source**: [PyInstaller antivirus discussion](https://github.com/orgs/pyinstaller/discussions/5877)

---

## Build System File Structure

```
build/
└── windows/
    ├── deskpulse.spec        # PyInstaller configuration
    ├── build.ps1             # Build automation script
    ├── installer.iss         # Inno Setup configuration
    ├── README.md             # This file
    ├── build.log             # Build output log (generated)
    └── Output/               # Inno Setup output (generated)
        └── DeskPulse-Setup-v1.0.0.exe

assets/
└── windows/
    ├── icon.ico              # Multi-resolution application icon
    ├── generate_icon.py      # Icon generation script
    └── verify_icon.py        # Icon verification script

dist/                         # PyInstaller output (generated)
└── DeskPulse/
    ├── DeskPulse.exe         # Main executable
    ├── python313.dll         # Python runtime
    ├── _internal/            # Dependencies
    │   ├── *.dll             # Windows DLLs
    │   ├── *.pyd             # Python extensions
    │   └── base_library.zip  # Standard library
    └── assets/
        └── icon.ico          # Bundled icon
```

---

## References

### Official Documentation

- **PyInstaller**: https://pyinstaller.org/en/stable/
  - [Using PyInstaller](https://pyinstaller.org/en/stable/usage.html)
  - [Operating Mode](https://pyinstaller.org/en/stable/operating-mode.html)
  - [Spec Files](https://pyinstaller.org/en/stable/spec-files.html)
  - [When Things Go Wrong](https://pyinstaller.org/en/stable/when-things-go-wrong.html)

- **Inno Setup**: https://jrsoftware.org/isinfo.php
  - [Documentation](https://jrsoftware.org/ishelp/)
  - [Run Section](https://jrsoftware.org/ishelp/topic_runsection.htm)
  - [Installation Considerations](http://www.vincenzo.net/isxkb/index.php?title=Installation_considerations)
  - [FAQ](https://jrsoftware.org/isfaq.php)

### Story Documentation

- **Story file**: `docs/sprint-artifacts/7-5-windows-installer-with-pyinstaller.md`
- **Epic 7**: `docs/sprint-artifacts/epic-7-windows-desktop-client.md`
- **Sprint status**: `docs/sprint-artifacts/sprint-status.yaml`

---

## Support

For issues or questions:
- **Repository Issues**: http://192.168.10.126:2221/Emeka/deskpulse/issues
- **Story documentation**: See `docs/sprint-artifacts/7-5-windows-installer-with-pyinstaller.md`
- **Build script**: See `build/windows/build.ps1` for detailed error messages

---

**Build system created**: 2026-01-05
**Version**: 1.0.0
**Agent**: Dev Agent Amelia (BMAD Method)
**Story**: 7-5-windows-installer-with-pyinstaller
