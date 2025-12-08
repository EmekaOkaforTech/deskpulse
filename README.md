# DeskPulse

Real-time posture monitoring system for Raspberry Pi.

DeskPulse uses computer vision and pose detection to monitor sitting posture and provide timely alerts to encourage better ergonomics and reduce health risks associated with prolonged poor posture.

## Features

- Real-time posture monitoring using MediaPipe
- Desktop and browser notifications
- Daily statistics and progress tracking
- Web dashboard for monitoring
- Runs on Raspberry Pi (4 or 5)

## Requirements

- Raspberry Pi 4 or 5 (4GB+ RAM recommended)
- 64-bit Raspberry Pi OS
- Python 3.9+
- USB camera

## Quick Start

Coming soon - one-line installation script.

## Development

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Running Development Server

```bash
source venv/bin/activate
python run.py
```

## Service Management (Production)

DeskPulse runs as a systemd service for automatic startup and crash recovery.

### Installation

```bash
sudo ./scripts/install_service.sh
```

### Service Commands

```bash
# Start the service
sudo systemctl start deskpulse.service

# Stop the service
sudo systemctl stop deskpulse.service

# Restart the service
sudo systemctl restart deskpulse.service

# Check status
sudo systemctl status deskpulse.service

# View logs
journalctl -u deskpulse -f
```

### Enable Local Network Access

By default, DeskPulse binds to localhost only for security. To enable access from other devices on your local network:

```bash
# Create override directory
sudo mkdir -p /etc/systemd/system/deskpulse.service.d/

# Create override file
sudo tee /etc/systemd/system/deskpulse.service.d/override.conf <<EOF
[Service]
Environment="FLASK_HOST=0.0.0.0"
EOF

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart deskpulse.service
```

See documentation for complete development setup instructions.

## License

TBD
