#!/bin/bash
# DeskPulse One-Line Installer
# Usage: curl -fsSL <url> | bash
#   Or: bash install.sh [--help|--uninstall|--update|--version <tag>|--yes]

set -e          # Exit on error
set -u          # Exit on undefined variable
set -o pipefail # Exit on pipe failure

# === Configuration ===
TOTAL_STEPS=11
REPO_URL="git@192.168.10.126:Emeka/deskpulse.git"
INSTALL_DIR="$HOME/deskpulse"
VERSION="${VERSION:-main}"  # Support VERSION=v1.0.0 curl | bash
INTERACTIVE=true

# === Logging ===
INSTALL_LOG="/tmp/deskpulse-install-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$INSTALL_LOG") 2>&1
echo "Installation log: $INSTALL_LOG"

# === Colors ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# === Cleanup Trap ===
cleanup() {
    echo -e "${RED}ERROR: Installation failed!${NC}"
    echo "Cleaning up partial installation..."
    rm -rf "$INSTALL_DIR"
    echo "Cleanup complete. Safe to retry."
    echo "Log saved: $INSTALL_LOG"
}
trap cleanup ERR

# === Helper Functions ===
STEP=0
progress() {
    STEP=$((STEP + 1))
    echo ""
    echo -e "${GREEN}[$STEP/$TOTAL_STEPS]${NC} $1"
}

error() {
    echo -e "${RED}ERROR:${NC} $1" >&2
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1"
}

# === Prerequisite Checks (AC2) ===
check_prerequisites() {
    progress "Checking prerequisites (~10 seconds)..."

    # Hardware check
    if ! grep -qE "Cortex-A72|A76" /proc/cpuinfo; then
        error "Raspberry Pi 3 not supported (detected: $(grep 'model name' /proc/cpuinfo | head -1))"
        echo "deskpulse requires Raspberry Pi 4 or 5"
        exit 1
    fi
    success "Raspberry Pi 4/5 detected"

    # OS check
    if ! grep -qE "ID=raspbian|ID=debian" /etc/os-release; then
        error "Requires Raspberry Pi OS or Debian"
        exit 1
    fi
    success "Raspberry Pi OS detected"

    # Python version check
    PY_VERSION=$(python3 --version | grep -oP '3\.\d+' | cut -d. -f2)
    if [ "$PY_VERSION" -lt 9 ]; then
        error "Python 3.9+ required, found 3.$PY_VERSION"
        exit 1
    fi
    success "Python 3.$PY_VERSION"

    # Python venv module check (E4)
    if ! python3 -m venv --help &>/dev/null; then
        error "python3-venv module not available"
        echo "Install with: sudo apt-get install python3-venv"
        exit 1
    fi
    success "python3-venv module available"

    # RAM check
    RAM_MB=$(free -m | awk '/Mem:/ {print $7}')
    if [ "$RAM_MB" -lt 4096 ]; then
        error "4GB+ RAM required, found ${RAM_MB}MB available"
        exit 1
    fi
    success "$((RAM_MB / 1024))GB RAM available"

    # Disk space check (18GB = 16 + 2 for MediaPipe) (E2)
    DISK_GB=$(df -BG ~/ | awk 'NR==2 {print $4}' | tr -d 'G')
    if [ "$DISK_GB" -lt 18 ]; then
        error "18GB+ free disk space required, found ${DISK_GB}GB"
        echo "DeskPulse needs 16GB + 2GB for AI models"
        exit 1
    fi
    success "${DISK_GB}GB free disk space"

    # Network check (E3)
    if ! curl -f -s -m 5 https://github.com >/dev/null; then
        error "No internet connection"
        echo "deskpulse installation requires internet for downloads"
        exit 1
    fi
    success "Internet connectivity verified"

    # systemd check (E7)
    if ! command -v systemctl &>/dev/null; then
        error "systemd not found"
        echo "deskpulse requires systemd for service management"
        exit 1
    fi
    success "systemd available"

    # Existing service check (E5)
    if systemctl is-active --quiet deskpulse.service 2>/dev/null; then
        error "deskpulse service already running"
        echo "Stop it first: sudo systemctl stop deskpulse.service"
        exit 1
    fi
    success "No existing service running"
}

# === Installation Steps (AC3-AC11) ===
install_system_dependencies() {
    progress "Installing system dependencies (~2 minutes)..."
    sudo apt-get update -qq
    sudo apt-get install -y python3-venv python3-pip libsystemd-dev libnotify-bin v4l-utils git
    sudo usermod -a -G video "$USER"
    success "System packages installed"
    warning "Logout/login required for camera access (video group)"
}

clone_repository() {
    progress "Cloning deskpulse repository (~30 seconds)..."

    # Check if directory exists (E5)
    if [ -d "$INSTALL_DIR" ]; then
        error "Directory $INSTALL_DIR already exists"
        echo "Options:"
        echo "  Reinstall: rm -rf $INSTALL_DIR && curl -fsSL <url> | bash"
        echo "  Update: cd $INSTALL_DIR && git pull && ./scripts/install.sh --update"
        exit 1
    fi

    # Validate URL reachable (E11)
    if ! curl -f -s -I "$REPO_URL" >/dev/null 2>&1; then
        error "Repository not found: $REPO_URL"
        exit 1
    fi

    # Clone with optional version (E12)
    cd ~
    if [ "$VERSION" != "main" ]; then
        git clone --branch "$VERSION" "$REPO_URL" || {
            error "Version $VERSION not found"
            exit 1
        }
    else
        git clone "$REPO_URL"
    fi
    cd deskpulse
    success "Repository cloned to $INSTALL_DIR"
}

setup_python_venv() {
    progress "Setting up Python environment (~5 minutes)..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools wheel -q
    pip install -r requirements.txt -q
    PKG_COUNT=$(pip list --format=freeze | wc -l)
    success "Virtual environment created"
    success "$PKG_COUNT packages installed"
}

verify_camera() {
    progress "Checking for camera..."

    # Fixed camera detection logic (C4)
    if v4l2-ctl --list-devices 2>/dev/null | grep -q "/dev/video"; then
        CAMERA_NAME=$(v4l2-ctl --list-devices 2>/dev/null | head -1)
        success "Camera detected: $CAMERA_NAME"
    else
        warning "No camera detected"
        echo "   deskpulse requires USB webcam for posture detection"
        echo "   You can add camera later and restart service"
    fi
}

download_mediapipe_models() {
    progress "Downloading AI models (~8 minutes - please wait)..."

    echo "MediaPipe downloading ~2GB models (no progress available)"
    echo "This may take 5-10 minutes depending on connection speed..."

    # Show spinner instead of impossible progress bar (C5)
    source venv/bin/activate
    python3 -c "import mediapipe as mp; mp.solutions.pose.Pose()" &
    PID=$!

    # Spinner while downloading
    while kill -0 $PID 2>/dev/null; do
        echo -n "."
        sleep 2
    done
    echo ""

    # Check if download succeeded
    wait $PID || {
        error "MediaPipe model download failed"
        echo "Check internet connection and retry"
        exit 1
    }

    success "MediaPipe models downloaded to ~/.cache/mediapipe/"
}

generate_secret_key() {
    progress "Generating secure secret key..."
    SECRET_KEY=$(openssl rand -hex 32)
    sudo mkdir -p /etc/deskpulse
    echo "DESKPULSE_SECRET_KEY=$SECRET_KEY" | sudo tee /etc/deskpulse/secrets.env >/dev/null
    sudo chmod 600 /etc/deskpulse/secrets.env
    success "Secret key generated (64-char hex, 256 bits entropy)"
}

setup_configuration() {
    progress "Setting up configuration..."

    # Verify config template exists (dependency check)
    if [ ! -f "scripts/templates/config.ini.example" ]; then
        error "Missing config.ini.example template"
        echo "Story 1.3 dependency missing: scripts/templates/config.ini.example"
        exit 1
    fi

    # Only copy config.ini, NOT secrets.env (C7 fix)
    sudo cp scripts/templates/config.ini.example /etc/deskpulse/config.ini
    sudo chmod 644 /etc/deskpulse/config.ini
    mkdir -p ~/.config/deskpulse
    success "Configuration files created"
}

initialize_database() {
    progress "Initializing database..."

    # Verify app factory exists (dependency check)
    if [ ! -f "app/__init__.py" ] || [ ! -f "app/data/database.py" ]; then
        error "Missing application files"
        echo "Story 1.1/1.2 dependencies missing: app/__init__.py or app/data/database.py"
        exit 1
    fi

    sudo mkdir -p /var/lib/deskpulse
    sudo chown "$USER:$USER" /var/lib/deskpulse

    source venv/bin/activate
    PYTHONPATH=. venv/bin/python3 << 'EOF'
from app import create_app
app = create_app('production')
with app.app_context():
    from app.data.database import init_db
    init_db()
EOF

    success "Database initialized at /var/lib/deskpulse/posture.db (WAL mode)"
}

install_systemd_service() {
    progress "Installing systemd service..."

    # Verify service file exists (dependency check)
    if [ ! -f "scripts/systemd/deskpulse.service" ]; then
        error "Missing service file"
        echo "Story 1.4 dependency missing: scripts/systemd/deskpulse.service"
        exit 1
    fi

    sudo cp scripts/systemd/deskpulse.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable deskpulse.service
    sudo systemctl start deskpulse.service
    success "Service installed and started"
    success "Auto-start enabled for boot"
}

verify_installation() {
    progress "Verifying installation..."

    # Allow Flask startup time
    sleep 5

    # Check service running
    if ! systemctl is-active --quiet deskpulse.service; then
        error "Service failed to start"
        echo "Check logs: journalctl -u deskpulse -n 50"
        exit 1
    fi
    success "Service running"

    # Check HTTP responding (requires AC0 health endpoint!) (C1 dependency)
    if ! curl -f -s http://localhost:5000/health >/dev/null; then
        error "Service not responding to HTTP"
        echo "Check logs: journalctl -u deskpulse -n 50"
        exit 1
    fi
    success "HTTP health check passed"

    # Check for errors in recent logs
    if journalctl -p err -u deskpulse --since "1 minute ago" 2>/dev/null | grep -q "ERROR"; then
        warning "Errors detected in logs"
        echo "   Review: journalctl -u deskpulse -p err -n 20"
    fi
}

display_success_message() {
    progress "Installation complete!"

    cat << 'EOF'

============================================
🎉 deskpulse Installation Complete! 🎉
============================================

Installation Summary:
  Location:  ~/deskpulse
  Database:  /var/lib/deskpulse/posture.db
  Config:    /etc/deskpulse/config.ini
  Service:   deskpulse.service (running ✓)

⚠️  IMPORTANT NEXT STEP:
  → Log out and log back in for camera access to work
    (Required for 'video' group membership to take effect)

Then:
  1. Open http://raspberrypi.local:5000 in your browser
  2. Position your webcam to see your shoulders
  3. Check logs: journalctl -u deskpulse -f

Troubleshooting:
  View logs:      journalctl -u deskpulse -f
  Service status: sudo systemctl status deskpulse
  Restart:        sudo systemctl restart deskpulse
  Stop:           sudo systemctl stop deskpulse

Documentation:
  http://192.168.10.126:2221/Emeka/deskpulse

Need help? File issues:
  http://192.168.10.126:2221/Emeka/deskpulse/issues
============================================

EOF
}

# === Lifecycle Functions ===
uninstall() {
    echo "deskpulse Uninstall"
    echo "==================="
    echo ""

    # Prompt for data deletion
    if [ "$INTERACTIVE" = true ]; then
        read -p "Delete database (contains your posture data)? [y/N]: " DELETE_DATA
    else
        DELETE_DATA="n"
    fi

    # Stop and disable service
    if systemctl is-active --quiet deskpulse.service 2>/dev/null; then
        sudo systemctl stop deskpulse.service
        echo "✓ Service stopped"
    fi

    if systemctl is-enabled --quiet deskpulse.service 2>/dev/null; then
        sudo systemctl disable deskpulse.service
        echo "✓ Service disabled"
    fi

    # Remove service file
    if [ -f /etc/systemd/system/deskpulse.service ]; then
        sudo rm /etc/systemd/system/deskpulse.service
        sudo systemctl daemon-reload
        echo "✓ Service file removed"
    fi

    # Remove database if requested
    if [[ "$DELETE_DATA" =~ ^[Yy]$ ]]; then
        sudo rm -rf /var/lib/deskpulse
        echo "✓ Database deleted"
    else
        echo "ℹ Database preserved at /var/lib/deskpulse/"
    fi

    # Remove config
    sudo rm -rf /etc/deskpulse
    echo "✓ Configuration removed"

    # Remove repository
    rm -rf ~/deskpulse
    echo "✓ Repository removed"

    echo ""
    echo "Uninstall complete!"
}

update() {
    echo "deskpulse Update"
    echo "================"
    echo ""

    cd ~/deskpulse || {
        error "deskpulse not found at ~/deskpulse"
        exit 1
    }

    # Capture current version for rollback (E1)
    CURRENT_VERSION=$(git describe --tags 2>/dev/null || git rev-parse --short HEAD)
    echo "Current version: $CURRENT_VERSION"

    # Setup rollback trap (E1)
    trap 'echo "Update failed! Rolling back..."; git checkout $CURRENT_VERSION; sudo systemctl restart deskpulse.service; exit 1' ERR

    # Stop service
    sudo systemctl stop deskpulse.service
    echo "✓ Service stopped"

    # Backup database (E1)
    BACKUP_FILE="/var/lib/deskpulse/posture.db.backup-$(date +%Y%m%d-%H%M%S)"
    cp /var/lib/deskpulse/posture.db "$BACKUP_FILE"
    echo "✓ Database backed up: $BACKUP_FILE"

    # Keep last 3 backups only
    ls -t /var/lib/deskpulse/posture.db.backup-* 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null || true

    # Update code
    git pull
    echo "✓ Code updated"

    # Update Python packages
    source venv/bin/activate
    pip install --upgrade -r requirements.txt -q
    echo "✓ Packages updated"

    # Run database migrations (E1)
    if grep -q "migrate_db" app/data/database.py; then
        PYTHONPATH=. venv/bin/python3 -c "from app.data.database import migrate_db; migrate_db()" || {
            error "Database migration failed"
            echo "Rolling back..."
            git checkout "$CURRENT_VERSION"
            sudo systemctl start deskpulse.service
            exit 1
        }
        echo "✓ Database migrations applied"
    fi

    # Restart service
    sudo systemctl start deskpulse.service
    echo "✓ Service restarted"

    # Verify service started (E1)
    sleep 3
    if ! systemctl is-active --quiet deskpulse.service; then
        error "Service failed to restart after update"
        echo "Rolling back to $CURRENT_VERSION..."
        git checkout "$CURRENT_VERSION"
        sudo systemctl start deskpulse.service
        exit 1
    fi

    NEW_VERSION=$(git describe --tags 2>/dev/null || git rev-parse --short HEAD)
    echo ""
    echo "✓ Update complete!"
    echo "  Old version: $CURRENT_VERSION"
    echo "  New version: $NEW_VERSION"

    # Clear rollback trap
    trap - ERR
}

show_help() {
    cat << 'EOF'
deskpulse Installer

Usage:
  # One-line install (direct):
  curl -fsSL http://192.168.10.126:2221/Emeka/deskpulse/raw/branch/main/scripts/install.sh | bash

  # Two-step install (secure):
  curl -fsSL http://192.168.10.126:2221/Emeka/deskpulse/raw/branch/main/scripts/install.sh -o install.sh
  bash install.sh

  # Local usage:
  ./scripts/install.sh [OPTIONS]

Options:
  --help              Show this help message
  --uninstall         Remove deskpulse (prompts for data deletion)
  --update            Update existing installation with rollback support
  --version <tag>     Install specific version (e.g., --version v1.0.0)
  --yes, -y           Non-interactive mode (use defaults)

Examples:
  # Install specific version:
  curl -fsSL <url> | VERSION=v1.0.0 bash

  # Non-interactive uninstall:
  ./scripts/install.sh --uninstall --yes

  # Update with automatic rollback on failure:
  ./scripts/install.sh --update

Documentation:
  http://192.168.10.126:2221/Emeka/deskpulse
EOF
}

# === Main ===
main() {
    # Parse arguments
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --uninstall)
            if [ "${2:-}" = "--yes" ] || [ "${2:-}" = "-y" ]; then
                INTERACTIVE=false
            fi
            uninstall
            exit 0
            ;;
        --update)
            update
            exit 0
            ;;
        --version)
            VERSION="${2:-main}"
            shift 2
            ;;
        --yes|-y)
            INTERACTIVE=false
            shift
            ;;
        "")
            # No arguments, proceed with install
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help for usage"
            exit 1
            ;;
    esac

    # Check if running as root (should NOT be)
    if [ $EUID -eq 0 ]; then
        error "Do not run installer as root"
        echo "Run as regular user (sudo will be requested when needed)"
        exit 1
    fi

    # Banner
    cat << 'EOF'
╔═══════════════════════════════════════╗
║   deskpulse Installation Wizard      ║
║   Version: 1.0.0                     ║
╚═══════════════════════════════════════╝

This will install deskpulse on your Raspberry Pi.
Estimated time: 15-20 minutes

EOF

    if [ "$INTERACTIVE" = true ]; then
        read -p "Press Enter to continue or Ctrl+C to cancel..."
    fi

    # Run installation
    check_prerequisites
    install_system_dependencies
    clone_repository
    setup_python_venv
    verify_camera
    download_mediapipe_models
    generate_secret_key
    setup_configuration
    initialize_database
    install_systemd_service
    verify_installation
    display_success_message

    # Clear error trap on success
    trap - ERR

    echo "Installation log saved: $INSTALL_LOG"
}

# Execute main
main "$@"
