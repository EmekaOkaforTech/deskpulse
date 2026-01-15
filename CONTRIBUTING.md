# Contributing to DeskPulse

Thank you for your interest in contributing to DeskPulse! This document provides guidelines and instructions for setting up your development environment and contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Development Setup

### Prerequisites

- Raspberry Pi 4 or 5 (for full testing)
- Python 3.9 or higher
- Git
- USB webcam (for testing camera features)

### 1. Clone Repository

```bash
git clone https://github.com/EmekaOkaforTech/deskpulse.git
cd deskpulse
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

Development dependencies include:
- pytest - Testing framework
- pytest-cov - Code coverage
- pytest-flask - Flask testing utilities
- flake8 - Linting

### 4. Set Up Configuration

```bash
# Create local config directory
mkdir -p ~/.config/deskpulse

# Copy example config (optional for development)
cp scripts/templates/config.ini.example ~/.config/deskpulse/config.ini
```

### 5. Initialize Development Database

```bash
# The database will be created automatically in /tmp for testing
# For development with persistent data:
PYTHONPATH=. python3 << 'EOF'
from app import create_app
app = create_app('development')
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

The development server will start on http://localhost:5000 with:
- Debug mode enabled
- Auto-reload on code changes
- Detailed error pages

## Running Tests

DeskPulse has comprehensive test coverage across all modules.

### Run All Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_config.py -v
```

### Run Tests with Coverage

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

### Run Tests by Category

```bash
# Configuration tests
pytest tests/test_config.py -v

# Database tests
pytest tests/test_database.py -v

# Factory pattern tests
pytest tests/test_factory.py -v

# Logging tests
pytest tests/test_logging.py -v

# systemd integration tests
pytest tests/test_systemd.py -v

# Installer tests
pytest tests/test_installer.py -v

# Health endpoint tests
pytest tests/test_routes.py -v
```

### Current Test Coverage

- **190 tests total**
- Unit tests for all core modules
- Integration tests for factory, database, config
- Installer verification tests (62 tests)
- systemd service tests
- Health endpoint tests

## Code Style

### Python Style Guide

We follow PEP 8 with some project-specific guidelines:

```bash
# Check code style
flake8 app/ tests/

# Configuration is in .flake8 file
```

**Key conventions:**
- Line length: 100 characters max
- Indentation: 4 spaces
- Use type hints for function signatures
- Write docstrings for public functions
- Import order: standard library, third-party, local

### Code Organization

- **Type hints**: Use for function parameters and return values
- **Docstrings**: Google-style docstrings for classes and public methods
- **Error handling**: Use custom exceptions from `app/core/exceptions.py`
- **Logging**: Use hierarchical logger names (`app.module.submodule`)
- **Configuration**: Access via Flask config, never hardcode values

### Example Code Style

```python
from typing import Optional, Dict, Any
from app.core.exceptions import ConfigurationError

def get_config_value(
    section: str,
    key: str,
    default: Optional[str] = None
) -> str:
    """Retrieve configuration value from INI file.

    Args:
        section: Configuration section name
        key: Configuration key within section
        default: Default value if key not found

    Returns:
        Configuration value as string

    Raises:
        ConfigurationError: If section/key not found and no default
    """
    # Implementation here
    pass
```

## Project Structure

```
deskpulse/
├── app/                    # Main application package
│   ├── __init__.py        # Flask application factory
│   ├── config.py          # Configuration management
│   ├── extensions.py      # Flask extensions (socketio, db)
│   ├── core/              # Core utilities
│   │   ├── constants.py   # Application constants
│   │   ├── exceptions.py  # Custom exceptions
│   │   └── logging.py     # Logging configuration
│   ├── data/              # Data layer
│   │   ├── database.py    # Database initialization
│   │   └── migrations/    # SQL schema migrations
│   ├── main/              # Main blueprint
│   │   ├── routes.py      # HTTP endpoints
│   │   └── events.py      # SocketIO events
│   ├── system/            # System integration
│   │   └── watchdog.py    # systemd watchdog
│   └── utils/             # Utility functions
├── tests/                 # Test suite
│   ├── conftest.py        # Pytest fixtures
│   ├── test_*.py          # Test modules
├── scripts/               # Installation and setup scripts
│   ├── install.sh         # One-line installer
│   ├── systemd/           # systemd service files
│   └── templates/         # Configuration templates
├── docs/                  # Documentation
│   ├── architecture.md    # System architecture
│   ├── prd.md            # Product requirements
│   └── sprint-artifacts/  # Development stories
├── run.py                 # Development server entry point
├── wsgi.py               # Production WSGI entry point
└── requirements.txt       # Python dependencies
```

### Key Architecture Patterns

- **Application Factory**: `app/__init__.py` creates Flask app instances
- **Blueprint Organization**: Features organized into Flask blueprints
- **Configuration Hierarchy**: System INI → User INI → Environment vars
- **Database Patterns**: SQLite with WAL mode, connection pooling
- **Logging**: Hierarchical loggers with systemd journal integration

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write code following the style guide
- Add tests for new functionality
- Update documentation if needed
- Ensure all tests pass

### 3. Test Your Changes

```bash
# Run full test suite
pytest tests/ -v

# Check code style
flake8 app/ tests/

# Verify test coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Brief description of changes

Detailed explanation if needed.

- Point 1
- Point 2
"
```

**Commit message guidelines:**
- First line: Brief summary (50 chars max)
- Blank line
- Detailed description (wrap at 72 chars)
- Reference issue numbers if applicable

## Submitting Changes

### 1. Push to Your Branch

```bash
git push origin feature/your-feature-name
```

### 2. Create a Pull Request

Visit https://github.com/EmekaOkaforTech/deskpulse and create a pull request with:

- Clear description of changes
- Reference to related issues
- Test coverage information
- Screenshots (if UI changes)

### 3. Code Review Process

- Maintain the code review etiquette
- Address feedback promptly
- Keep the PR focused on a single feature/fix
- Ensure CI checks pass

## Reporting Issues

### Before Reporting

1. Check existing issues: https://github.com/EmekaOkaforTech/deskpulse/issues
2. Verify it's reproducible
3. Check if it's already fixed in latest version

### Issue Template

```markdown
**Description:**
Clear description of the issue

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior:**
What should happen

**Actual Behavior:**
What actually happens

**Environment:**
- DeskPulse version:
- Raspberry Pi model:
- OS version:
- Python version:

**Logs:**
Relevant log output from `journalctl -u deskpulse -n 50`
```

## Development Workflow

### Typical Development Cycle

1. Pull latest changes: `git pull origin main`
2. Create feature branch: `git checkout -b feature/name`
3. Make changes and test locally
4. Run full test suite: `pytest tests/ -v`
5. Check code style: `flake8 app/ tests/`
6. Commit changes with clear message
7. Push to remote: `git push origin feature/name`
8. Create pull request
9. Address review feedback
10. Merge when approved

### Testing on Raspberry Pi

For features that require hardware testing:

1. Test on actual Raspberry Pi 4 or 5
2. Verify with real USB webcam
3. Test systemd service integration
4. Check performance under load
5. Verify camera permissions (video group)

### Testing Database Changes

```bash
# Test with temporary database
export DESKPULSE_DB_PATH=/tmp/test_posture.db
python run.py

# Test database migration
PYTHONPATH=. python3 -c "
from app import create_app
app = create_app('testing')
with app.app_context():
    from app.data.database import init_db
    init_db()
"
```

## Code Review Guidelines

### For Contributors

- Keep PRs focused and reasonably sized
- Write clear commit messages
- Add tests for new functionality
- Update documentation
- Respond to feedback constructively

### For Reviewers

- Be respectful and constructive
- Focus on code quality, not style preferences
- Test the changes locally if possible
- Approve when ready, request changes if needed

## Getting Help

- **Documentation**: https://github.com/EmekaOkaforTech/deskpulse
- **Issues**: https://github.com/EmekaOkaforTech/deskpulse/issues
- **Architecture Docs**: [docs/architecture.md](docs/architecture.md)
- **Test Design**: [docs/test-design.md](docs/test-design.md)

## License

By contributing to DeskPulse, you agree that your contributions will be licensed under the MIT License.
