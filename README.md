# DeskPulse - Privacy-First Posture Monitoring

Real-time posture monitoring for Raspberry Pi with local processing and zero cloud dependencies.

## Features

- **Real-time Monitoring**: Uses MediaPipe Tasks API for accurate posture detection (Story 8.2)
- **Privacy-First**: All processing runs locally on your Raspberry Pi - no data leaves your device
- **Smart Alerts**: Configurable thresholds with desktop and browser notifications
- **Progress Tracking**: Historical data and trend analysis
- **Easy Setup**: One-line installer with automatic configuration
- **systemd Integration**: Runs as a service with automatic startup

## Quick Install (Raspberry Pi)

```bash
curl -fsSL http://192.168.10.126:2221/Emeka/deskpulse/raw/branch/main/scripts/install.sh | bash
```

**Requirements:**
- Raspberry Pi 4 or 5 (4GB+ RAM recommended)
- Raspberry Pi OS (64-bit)
- USB webcam (Logitech C270 or compatible)
- Internet connection for initial setup

**What it does:**
- Checks system prerequisites (hardware, OS, Python 3.9+)
- Installs system dependencies (v4l-utils, libnotify)
- Clones repository and creates Python virtual environment
- Downloads MediaPipe Pose landmarker model files (~9MB .task files)
- Configures systemd service with auto-start
- Verifies installation with health check

**Installation time:** ~15-20 minutes (depends on internet speed for model download)

**After installation:**
1. **Log out and log back in** (required for camera permissions)
2. Open http://raspberrypi.local:5000 in your browser
3. Position your webcam to see your shoulders and head

## Manual Installation

If you prefer manual setup or need to customize the installation:

### 1. Prerequisites

```bash
# Check your Pi model (must be Pi 4 or 5)
cat /proc/cpuinfo | grep "Model"

# Check Python version (must be 3.9+)
python3 --version

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip git v4l-utils libnotify-bin
```

### 2. Clone Repository

```bash
git clone git@192.168.10.126:Emeka/deskpulse.git
cd deskpulse
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure

```bash
# Copy example configuration
sudo mkdir -p /etc/deskpulse
sudo cp scripts/templates/config.ini.example /etc/deskpulse/config.ini

# Generate secret key
sudo bash -c 'echo "DESKPULSE_SECRET_KEY=$(openssl rand -hex 32)" > /etc/deskpulse/secrets.env'
sudo chmod 600 /etc/deskpulse/secrets.env
```

### 5. Initialize Database

```bash
PYTHONPATH=. venv/bin/python3 << 'EOF'
from app import create_app
app = create_app('production')
with app.app_context():
    from app.data.database import init_db
    init_db()
EOF
```

### 6. Run Development Server

```bash
source venv/bin/activate
python run.py
```

Open http://localhost:5000 in your browser.

### 7. Install as systemd Service (Optional)

```bash
sudo cp scripts/systemd/deskpulse.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable deskpulse.service
sudo systemctl start deskpulse.service
```

## Usage

### Access Dashboard

- **Local:** http://localhost:5000
- **Network:** http://raspberrypi.local:5000
- **IP Address:** http://YOUR_PI_IP:5000

### Configuration

Edit configuration at `~/.config/deskpulse/config.ini` or `/etc/deskpulse/config.ini`:

```ini
[camera]
device = 0                    # Camera device (/dev/video0)
resolution = 720p             # 480p, 720p, or 1080p
fps_target = 10               # Frames per second

[alerts]
posture_threshold_minutes = 10  # Minutes before alert
notification_enabled = true     # Desktop notifications

[dashboard]
port = 5000                     # Web dashboard port
update_interval_seconds = 2     # Real-time update frequency
```

User config (`~/.config/deskpulse/config.ini`) overrides system config.

### Service Management

```bash
# Check status
sudo systemctl status deskpulse

# View logs
journalctl -u deskpulse -f

# Restart service
sudo systemctl restart deskpulse

# Stop service
sudo systemctl stop deskpulse

# Disable auto-start
sudo systemctl disable deskpulse
```

### Pause Monitoring

Click the "Pause" button in the dashboard when you need to step away.

### Update DeskPulse

```bash
cd ~/deskpulse
./scripts/install.sh --update
```

Updates with automatic rollback on failure.

### Uninstall

```bash
cd ~/deskpulse
./scripts/install.sh --uninstall
```

Optionally preserves your posture history database.

## Windows Desktop Client

DeskPulse includes a native Windows desktop client that runs in your system tray and connects to your Raspberry Pi backend.

### Features

- **System Tray Integration**: Runs quietly in background, accessible from tray icon
- **Real-time Notifications**: Toast notifications for alerts and status updates
- **Live Stats**: View today's posture statistics from tray menu
- **Pause/Resume Control**: Pause monitoring when stepping away
- **Auto-Start Option**: Launch automatically when Windows starts
- **No Python Required**: Standalone installer - works on any Windows 10/11 PC

### Quick Install

1. **Download installer**: [DeskPulse-Setup-v1.0.0.exe](http://192.168.10.126:2221/Emeka/deskpulse/releases)
2. **Run installer**: Double-click the downloaded file
   - Windows may show SmartScreen warning (click "More info" → "Run anyway")
   - This is normal for unsigned open-source software
3. **Follow wizard**: Choose installation location and options
4. **Launch DeskPulse**: Starts automatically after installation

### Requirements

- **Windows 10 (1803+) or Windows 11** (64-bit)
- **Raspberry Pi** with DeskPulse backend running on same network
- **No Python installation needed** - completely standalone

### Configuration

On first launch, DeskPulse creates config at: `%APPDATA%\DeskPulse\config.json`

**Default backend**: `http://raspberrypi.local:5000`

**To change backend URL**:
1. Right-click tray icon → "Exit"
2. Edit: `C:\Users\YourName\AppData\Roaming\DeskPulse\config.json`
   ```json
   {
     "backend_url": "http://192.168.1.100:5000"
   }
   ```
3. Restart DeskPulse

### System Tray Menu

Right-click the tray icon to access:
- **Pause/Resume Monitoring**: Control monitoring state
- **View Stats → Today's Stats**: See your posture statistics
- **Open Dashboard**: Launch backend dashboard in browser
- **Exit**: Close DeskPulse

### Building from Source (Advanced)

See [build/windows/README.md](build/windows/README.md) for detailed build instructions.

**Quick build** (requires Python 3.9+, PyInstaller):
```powershell
.\build\windows\build.ps1
```

**Output**: `dist/DeskPulse/DeskPulse.exe`

## Troubleshooting

### Camera Not Detected

```bash
# List available cameras
v4l2-ctl --list-devices

# Test camera
ffplay /dev/video0

# Check permissions (must be in 'video' group)
groups | grep video
```

If not in video group, log out and log back in after installation.

### Service Won't Start

```bash
# Check logs
journalctl -u deskpulse -n 50

# Check configuration
cat /etc/deskpulse/config.ini

# Verify secret key exists
sudo cat /etc/deskpulse/secrets.env
```

### Dashboard Not Accessible

```bash
# Check if service is running
sudo systemctl status deskpulse

# Check port binding
sudo netstat -tlnp | grep 5000

# Test health endpoint
curl http://localhost:5000/health
```

### High CPU Usage

Reduce FPS in configuration:

```ini
[camera]
fps_target = 5    # Lower value = less CPU
resolution = 480p # Lower resolution helps
```

### MediaPipe Installation Failed

**Story 8.2:** DeskPulse now uses MediaPipe Tasks API with platform-specific versions:

**Raspberry Pi (ARM64):**
```bash
source venv/bin/activate
pip install mediapipe==0.10.18 --no-cache-dir
```

**Windows/Linux (x86_64):**
```bash
source venv/bin/activate
pip install mediapipe==0.10.31 --no-cache-dir
```

**Model Files:**
If model files are missing, download manually:
```bash
mkdir -p app/cv/models
cd app/cv/models
curl -L -o pose_landmarker_full.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
```

## Documentation

- **[Architecture](docs/architecture.md)** - System design and technical decisions
- **[PRD](docs/prd.md)** - Product requirements and features
- **[UX Design](docs/ux-design-specification.md)** - User experience specification
- **[Test Design](docs/test-design.md)** - Testing strategy and architecture
- **[Epics](docs/epics.md)** - Feature breakdown and user stories
- **[Contributing](CONTRIBUTING.md)** - Development setup and guidelines

## Project Status

**Epic 1: Foundation Setup & Installation** ✅ Complete
- Flask application with factory pattern
- SQLite database with WAL mode
- Configuration management system
- systemd service integration
- Comprehensive logging
- One-line installer script
- Development documentation

**Next:** Epic 2 - Real-Time Posture Monitoring

## Repository

- **Git:** git@192.168.10.126:Emeka/deskpulse.git
- **Web:** http://192.168.10.126:2221/Emeka/deskpulse
- **Issues:** http://192.168.10.126:2221/Emeka/deskpulse/issues

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

- **Issues:** http://192.168.10.126:2221/Emeka/deskpulse/issues
- **Documentation:** http://192.168.10.126:2221/Emeka/deskpulse

## Acknowledgments

Built with:
- Flask 3.0.0 - Web framework
- MediaPipe Tasks API (0.10.31/0.10.18) - Pose detection (Story 8.2)
- OpenCV - Computer vision
- SQLite - Database
- systemd - Service management
