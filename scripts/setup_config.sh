#!/bin/bash
# DeskPulse Configuration Setup Script
# =====================================
# Sets up system and user configuration files for DeskPulse.
#
# Usage:
#   ./scripts/setup_config.sh          # Interactive setup
#   ./scripts/setup_config.sh --system # System config only (requires sudo)
#   ./scripts/setup_config.sh --user   # User config only
#   ./scripts/setup_config.sh --all    # Both system and user config

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/templates"
SYSTEM_CONFIG_DIR="/etc/deskpulse"
USER_CONFIG_DIR="${HOME}/.config/deskpulse"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

generate_secret_key() {
    # Generate a secure 64-character hex secret key
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

setup_system_config() {
    print_info "Setting up system configuration..."

    # Check for sudo access
    if [[ $EUID -ne 0 ]]; then
        print_error "System config setup requires root privileges."
        print_info "Run with: sudo ./scripts/setup_config.sh --system"
        return 1
    fi

    # Create system config directory
    if [[ ! -d "${SYSTEM_CONFIG_DIR}" ]]; then
        mkdir -p "${SYSTEM_CONFIG_DIR}"
        print_info "Created ${SYSTEM_CONFIG_DIR}"
    fi

    # Copy config.ini template
    if [[ ! -f "${SYSTEM_CONFIG_DIR}/config.ini" ]]; then
        cp "${TEMPLATE_DIR}/config.ini.example" "${SYSTEM_CONFIG_DIR}/config.ini"
        chmod 644 "${SYSTEM_CONFIG_DIR}/config.ini"
        print_info "Created ${SYSTEM_CONFIG_DIR}/config.ini"
    else
        print_warn "${SYSTEM_CONFIG_DIR}/config.ini already exists, skipping"
    fi

    # Copy config.ini.example for reference
    cp "${TEMPLATE_DIR}/config.ini.example" "${SYSTEM_CONFIG_DIR}/config.ini.example"
    chmod 644 "${SYSTEM_CONFIG_DIR}/config.ini.example"

    # Create secrets.env with generated key
    if [[ ! -f "${SYSTEM_CONFIG_DIR}/secrets.env" ]]; then
        SECRET_KEY=$(generate_secret_key)
        echo "# DeskPulse Secrets - Generated $(date -I)" > "${SYSTEM_CONFIG_DIR}/secrets.env"
        echo "DESKPULSE_SECRET_KEY=${SECRET_KEY}" >> "${SYSTEM_CONFIG_DIR}/secrets.env"
        chmod 600 "${SYSTEM_CONFIG_DIR}/secrets.env"
        print_info "Created ${SYSTEM_CONFIG_DIR}/secrets.env with secure random key"
        print_info "Permissions set to 600 (root only)"
    else
        print_warn "${SYSTEM_CONFIG_DIR}/secrets.env already exists, skipping"
    fi

    print_info "System configuration complete!"
}

setup_user_config() {
    print_info "Setting up user configuration..."

    # Create user config directory
    if [[ ! -d "${USER_CONFIG_DIR}" ]]; then
        mkdir -p "${USER_CONFIG_DIR}"
        print_info "Created ${USER_CONFIG_DIR}"
    fi

    # Copy config.ini template for user overrides
    if [[ ! -f "${USER_CONFIG_DIR}/config.ini" ]]; then
        # Create a minimal user config with comments
        cat > "${USER_CONFIG_DIR}/config.ini" << 'EOF'
# DeskPulse User Configuration
# ============================
# Add your personal overrides here.
# These settings take precedence over /etc/deskpulse/config.ini
#
# Only uncomment and modify settings you want to change.
# See /etc/deskpulse/config.ini.example for all available options.

# [camera]
# device = 0

# [alerts]
# posture_threshold_minutes = 10

# [dashboard]
# port = 5000
EOF
        chmod 644 "${USER_CONFIG_DIR}/config.ini"
        print_info "Created ${USER_CONFIG_DIR}/config.ini"
    else
        print_warn "${USER_CONFIG_DIR}/config.ini already exists, skipping"
    fi

    print_info "User configuration complete!"
}

show_usage() {
    echo "DeskPulse Configuration Setup"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --system   Setup system configuration only (requires sudo)"
    echo "  --user     Setup user configuration only"
    echo "  --all      Setup both system and user configuration"
    echo "  --help     Show this help message"
    echo ""
    echo "Without options, runs in interactive mode."
}

# Parse command line arguments
case "$1" in
    --system)
        setup_system_config
        ;;
    --user)
        setup_user_config
        ;;
    --all)
        if [[ $EUID -eq 0 ]]; then
            setup_system_config
            # Switch to non-root user for user config
            if [[ -n "${SUDO_USER}" ]]; then
                su - "${SUDO_USER}" -c "mkdir -p ${USER_CONFIG_DIR}"
                print_info "User config directory created. Run again as regular user for user config."
            fi
        else
            print_warn "Running without root - setting up user config only"
            print_info "For system config, run: sudo $0 --system"
            setup_user_config
        fi
        ;;
    --help)
        show_usage
        ;;
    "")
        # Interactive mode
        echo "DeskPulse Configuration Setup"
        echo "=============================="
        echo ""
        echo "This script will set up DeskPulse configuration files."
        echo ""
        echo "1. System config (/etc/deskpulse/) - requires sudo"
        echo "2. User config (~/.config/deskpulse/)"
        echo "3. Both"
        echo ""
        read -p "Choose option [1/2/3]: " choice
        case "$choice" in
            1)
                if [[ $EUID -ne 0 ]]; then
                    print_error "Please run with sudo for system config"
                    exit 1
                fi
                setup_system_config
                ;;
            2)
                setup_user_config
                ;;
            3)
                if [[ $EUID -eq 0 ]]; then
                    setup_system_config
                    print_info "Run again as regular user for user config"
                else
                    print_warn "Need sudo for system config. Setting up user config only."
                    setup_user_config
                fi
                ;;
            *)
                print_error "Invalid option"
                exit 1
                ;;
        esac
        ;;
    *)
        print_error "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac

echo ""
print_info "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit ${SYSTEM_CONFIG_DIR}/config.ini for system defaults"
echo "  2. Edit ${USER_CONFIG_DIR}/config.ini for personal overrides"
echo "  3. Start DeskPulse: flask run"
