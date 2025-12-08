#!/bin/bash
# DeskPulse systemd Service Installation Script
#
# This script installs and configures the DeskPulse systemd service for
# automatic startup on boot and crash recovery.
#
# Usage:
#   sudo ./scripts/install_service.sh [--enable-firewall]
#
# Options:
#   --enable-firewall  Configure ufw firewall rules (optional but recommended)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_FILE="$SCRIPT_DIR/systemd/deskpulse.service"
SYSTEMD_DIR="/etc/systemd/system"
ENABLE_FIREWALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --enable-firewall)
            ENABLE_FIREWALL=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}=== DeskPulse Service Installation ===${NC}"

# Check if service file exists
if [[ ! -f "$SERVICE_FILE" ]]; then
    echo -e "${RED}Error: Service file not found at $SERVICE_FILE${NC}"
    exit 1
fi

# Copy service file to systemd directory
echo -e "${YELLOW}Installing service file...${NC}"
cp "$SERVICE_FILE" "$SYSTEMD_DIR/deskpulse.service"
chmod 644 "$SYSTEMD_DIR/deskpulse.service"
echo -e "${GREEN}✓ Service file installed to $SYSTEMD_DIR/deskpulse.service${NC}"

# Reload systemd daemon
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ systemd daemon reloaded${NC}"

# Enable service for auto-start
echo -e "${YELLOW}Enabling service for auto-start on boot...${NC}"
systemctl enable deskpulse.service
echo -e "${GREEN}✓ Service enabled for auto-start${NC}"

# Configure firewall if requested
if [[ "$ENABLE_FIREWALL" == true ]]; then
    echo -e "${YELLOW}Configuring firewall...${NC}"

    # Check if ufw is installed
    if ! command -v ufw &> /dev/null; then
        echo -e "${YELLOW}Installing ufw...${NC}"
        apt-get update && apt-get install -y ufw
    fi

    # Allow SSH first (prevent lockout)
    ufw allow ssh

    # Allow DeskPulse only from local network
    ufw allow from 192.168.0.0/16 to any port 5000

    # Enable firewall if not already enabled
    if ! ufw status | grep -q "Status: active"; then
        echo -e "${YELLOW}Enabling firewall...${NC}"
        ufw --force enable
    fi

    echo -e "${GREEN}✓ Firewall configured${NC}"
    echo -e "${YELLOW}Firewall status:${NC}"
    ufw status
fi

# Print status and next steps
echo ""
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo -e "Service file: $SYSTEMD_DIR/deskpulse.service"
echo -e "Status: Enabled (will start on boot)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Start the service now:    ${GREEN}sudo systemctl start deskpulse.service${NC}"
echo -e "  2. Check service status:     ${GREEN}sudo systemctl status deskpulse.service${NC}"
echo -e "  3. View service logs:        ${GREEN}journalctl -u deskpulse -f${NC}"
echo ""
echo -e "${YELLOW}Service Control Commands:${NC}"
echo -e "  Start:   sudo systemctl start deskpulse.service"
echo -e "  Stop:    sudo systemctl stop deskpulse.service"
echo -e "  Restart: sudo systemctl restart deskpulse.service"
echo -e "  Status:  sudo systemctl status deskpulse.service"
echo ""
echo -e "${YELLOW}To enable local network access:${NC}"
echo -e "  1. Create override file:"
echo -e "     ${GREEN}sudo mkdir -p /etc/systemd/system/deskpulse.service.d/${NC}"
echo -e "     ${GREEN}sudo tee /etc/systemd/system/deskpulse.service.d/override.conf <<EOF"
echo -e "     [Service]"
echo -e "     Environment=\"FLASK_HOST=0.0.0.0\""
echo -e "     EOF${NC}"
echo -e "  2. Reload and restart:"
echo -e "     ${GREEN}sudo systemctl daemon-reload${NC}"
echo -e "     ${GREEN}sudo systemctl restart deskpulse.service${NC}"
