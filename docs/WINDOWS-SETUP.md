# DeskPulse Windows Client - Setup Runbook

**Version:** 1.0.0
**Date:** 2026-01-05
**Target:** Windows 10 (1803+) or Windows 11 (64-bit)

---

## Prerequisites

**Before starting:**
1. ✅ Raspberry Pi running DeskPulse backend
2. ✅ Know your Pi's IP address
3. ✅ Windows PC can reach Pi's network

**Check Pi backend:**
```bash
# On Pi, verify service is running:
sudo systemctl status deskpulse
# Should show: active (running)

# Get Pi IP address:
hostname -I
# Example: 192.168.10.133
```

---

## Setup Option A: Run from Source (Recommended for Testing)

**Time:** 10 minutes
**Requires:** Git, Python 3.9+ (64-bit)

### Step 1: Clone Repository

```powershell
# Open PowerShell
cd C:\Users\YourName\Desktop

# Clone from Gitea
git clone http://192.168.10.126:2221/Emeka/deskpulse.git
cd deskpulse
```

### Step 2: Install Dependencies

```powershell
# Install Python packages
pip install -r requirements.txt
```

### Step 3: Configure Backend URL

**Create config file:**
```powershell
# Create config directory
mkdir $env:APPDATA\DeskPulse

# Create config file
notepad $env:APPDATA\DeskPulse\config.json
```

**Add this content (replace IP with YOUR Pi's IP):**
```json
{
  "backend_url": "http://192.168.10.133:5000"
}
```

**Save and close Notepad.**

### Step 4: Run Client

```powershell
# Run from source
python -m app.windows_client
```

**✅ SUCCESS:** Green icon appears in system tray (bottom-right)

---

## Setup Option B: Build Installer (For Deployment)

**Time:** 5 minutes
**Requires:** Python 3.9+ (64-bit), PyInstaller

### Step 1: Build Executable

```powershell
# From project root
cd C:\path\to\deskpulse

# Run build script (2-5 minutes)
.\build\windows\build.ps1
```

**Output:** `dist\DeskPulse\DeskPulse.exe`

### Step 2: Run Executable

```powershell
.\dist\DeskPulse\DeskPulse.exe
```

**First run:** Client creates config at `%APPDATA%\DeskPulse\config.json`
**Default backend:** `http://raspberrypi.local:5000`

**If connection fails (cross-subnet):**
```powershell
# Stop client (right-click tray icon → Exit)

# Edit config with Pi's IP
notepad %APPDATA%\DeskPulse\config.json
```

Change to:
```json
{
  "backend_url": "http://192.168.10.133:5000"
}
```

**Save, restart client.**

---

## Cross-Subnet Networking

**Your Network Layout:**
- **Pi:** 192.168.10.133 (subnet A)
- **Windows:** 192.168.40.216 (subnet B)

**Test connectivity:**
```powershell
# Can Windows reach Pi?
ping 192.168.10.133

# Can Windows access backend?
curl http://192.168.10.133:5000
```

**If ping fails:**
1. Check router allows inter-VLAN routing
2. Check Pi firewall allows port 5000:
   ```bash
   sudo ufw status
   sudo ufw allow 5000/tcp
   ```

**If curl fails:**
1. Verify Pi backend is listening on all interfaces:
   ```bash
   # On Pi, check binding
   sudo netstat -tlnp | grep 5000
   # Should show: 0.0.0.0:5000 (not 127.0.0.1:5000)
   ```

---

## Feature Testing

**Once client is running:**

### 1. System Tray Icon
- ✅ **Green icon** = Connected
- ⚪ **Gray icon** = Paused
- 🔴 **Red icon** = Disconnected

### 2. Toast Notifications
- Wait 2-3 seconds after launch
- You'll see: "Connected to backend"

### 3. Pause/Resume
- Right-click tray icon → "Pause Monitoring"
- Icon turns **gray**
- Right-click → "Resume Monitoring"
- Icon turns **green**

### 4. View Stats
- Right-click tray icon → "View Stats" → "Today's Stats"
- Popup shows:
  ```
  Good Posture: XX min (XX%)
  Poor Posture: XX min (XX%)
  Alerts Triggered: X
  ```

### 5. Open Dashboard
- Right-click tray icon → "Open Dashboard"
- Browser opens: `http://192.168.10.133:5000`

### 6. Exit
- Right-click tray icon → "Exit"
- Client closes cleanly

---

## Troubleshooting

### Problem: No tray icon appears

**Solution:**
```powershell
# Check if client is running
Get-Process | Where-Object {$_.ProcessName -like "*DeskPulse*"}

# Kill stale processes
Stop-Process -Name DeskPulse -Force

# Restart client
```

### Problem: "Connection failed" notification

**Solution:**
```powershell
# 1. Verify Pi IP is reachable
ping 192.168.10.133

# 2. Edit config with correct IP
notepad %APPDATA%\DeskPulse\config.json

# 3. Restart client
```

### Problem: Stats show "No data available"

**Solution:**
- Wait 2-3 minutes after starting
- Ensure Pi backend is collecting posture data
- Check Pi dashboard shows live posture feed

### Problem: No toast notifications

**Solution:**
- Verify Windows notifications are enabled:
  - Settings → System → Notifications
  - Enable "Get notifications from apps and other senders"
- Requires Windows 10 (1803+) or Windows 11

### Problem: Icon stuck red

**Solution:**
```powershell
# Check backend reachability
curl http://192.168.10.133:5000

# Check client logs
notepad %APPDATA%\DeskPulse\logs\client.log
# Look for connection errors
```

---

## File Locations

**Config:**
```
C:\Users\YourName\AppData\Roaming\DeskPulse\config.json
```

**Logs:**
```
C:\Users\YourName\AppData\Roaming\DeskPulse\logs\client.log
```

**Executable (if built):**
```
C:\path\to\deskpulse\dist\DeskPulse\DeskPulse.exe
```

---

## Quick Start Checklist

For your specific setup (Pi: 192.168.10.133, Windows: 192.168.40.216):

```powershell
# 1. Clone repo
git clone http://192.168.10.126:2221/Emeka/deskpulse.git
cd deskpulse

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create config directory
mkdir $env:APPDATA\DeskPulse

# 4. Create config file
@"
{
  "backend_url": "http://192.168.10.133:5000"
}
"@ | Out-File -FilePath "$env:APPDATA\DeskPulse\config.json" -Encoding utf8

# 5. Test connectivity
curl http://192.168.10.133:5000

# 6. Run client
python -m app.windows_client
```

**✅ Expected:** Green tray icon appears within 5 seconds

---

## Support

**Repository:** http://192.168.10.126:2221/Emeka/deskpulse
**Issues:** http://192.168.10.126:2221/Emeka/deskpulse/issues
**Build Documentation:** See `build/windows/README.md` for installer creation
