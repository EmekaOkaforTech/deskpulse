---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: ['docs/prd.md', 'docs/ux-design-specification.md']
workflowType: 'architecture'
lastStep: 6
project_name: 'deskpulse'
user_name: 'Boss'
date: '2025-12-06'
completed: true
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

DeskPulse implements 60 functional requirements across 7 capability areas, forming a comprehensive IoT wellness monitoring system:

- **Posture Monitoring (FR1-FR7):** Real-time video capture at 5-15 FPS, MediaPipe Pose landmark detection, binary good/bad classification, presence detection, camera disconnect handling, and continuous 8+ hour operation
- **Alert & Notification System (FR8-FR13):** Configurable threshold detection (default 10 min), desktop notifications, visual dashboard alerts, privacy pause/resume controls, and monitoring status indication
- **Analytics & Reporting (FR14-FR23):** Local SQLite storage with timestamps, daily/weekly statistics, 7-day historical baseline, improvement trend calculation, optional pain tracking correlation, pattern detection, and CSV/PDF export
- **System Management (FR24-FR34):** One-line installer script, systemd auto-start, update checking from GitHub releases, database backup/rollback, configuration management, system status monitoring, logging, and camera calibration
- **Dashboard & Visualization (FR35-FR45):** Local network web access via mDNS, live camera feed with pose overlay, real-time WebSocket updates, multi-device simultaneous viewing, charts/graphs, break reminders, and customization
- **Data Management (FR46-FR52):** 100% local SQLite storage with WAL mode, 7-day free tier vs 30+ day Pro tier data retention, optional encryption, and user data deletion
- **Community & Contribution (FR53-FR60):** CONTRIBUTING.md documentation, good-first-issue labeling, development setup, CI/CD testing, GitHub issue tracking, comprehensive docs, changelog, and community forum

**Architecturally significant patterns:**
- Zero external dependencies during operation (purely local processing)
- Real-time processing pipeline: capture → inference → classification → storage → alert → UI update
- Multi-tier data retention (7-day free, 30+ Pro) requiring data lifecycle management
- Extensibility through community contributions and plugin potential

**Non-Functional Requirements:**

Critical NFRs that will drive architectural decisions:

**Performance (NFR-P1 to NFR-P4):**
- Real-time CV processing: 5+ FPS Pi 4, 10+ FPS Pi 5 sustained
- Dashboard responsiveness: <100ms posture change to UI update
- Startup time: <60 sec power-on to operational
- Resource efficiency: <2GB RAM, <80% CPU during operation

**Reliability (NFR-R1 to NFR-R5):**
- 99%+ uptime during 24/7 operation
- Auto-restart within 30 sec on crash (systemd)
- SQLite integrity during ungraceful shutdowns (WAL mode)
- Camera reconnection within 10 sec
- 8+ hour continuous operation without memory leaks

**Security & Privacy (NFR-S1 to NFR-S5):**
- Zero external network traffic (100% local processing)
- **Network Binding (NFR-S2):** Default to 127.0.0.1 (localhost), configurable via FLASK_HOST environment variable for local network access
- **Defense in Depth:** Application binding + OS firewall rules (ufw/nftables) to restrict access to local subnet only
- All data stored locally on Pi storage
- Clear camera recording indicator
- Optional HTTP basic auth for shared networks

**Maintainability (NFR-M1 to NFR-M5):**
- PEP 8 compliance with <10 linting violations per 1000 lines
- 70%+ unit test coverage on core logic
- NumPy/Google style docstrings on public APIs
- Structured logging (timestamps, severity, context)
- Database schema migrations preserve user data

**Scalability (NFR-SC1 to NFR-SC3):**
- 10+ simultaneous WebSocket dashboard connections
- 1+ year posture data (365 days × 8 hours × 10 FPS) with <10% query degradation
- <20% code modification to support new SBC platforms

**Usability (NFR-U1 to NFR-U3):**
- <30 min installation for technical users
- 80%+ common issues self-service via documentation
- 30%+ bad posture reduction visible within 3-4 days (drives retention)

**Scale & Complexity:**

- **Primary domain:** IoT/Embedded Full-Stack (edge computing + web dashboard + computer vision)
- **Complexity level:** Medium
  - Real-time CV processing is non-trivial but established libraries (MediaPipe, OpenCV) reduce ML complexity
  - Local-only architecture avoids distributed systems complexity
  - Inference only (no training pipeline)
  - Edge computing constraints drive optimization needs
- **Estimated architectural components:** 8-10 major components
  - CV capture and processing pipeline
  - Posture classification engine
  - Alert management system
  - Data persistence layer
  - Web server and API
  - WebSocket real-time communication
  - Dashboard UI (Pico CSS semantic HTML)
  - System service management (systemd)
  - Update and configuration management
  - (Future) Plugin/extension system

### Technical Constraints & Dependencies

**Hardware Platform Constraints:**
- **Raspberry Pi 4/5 only** (initial focus) - ARM CPU architecture without GPU acceleration
- **No Pi 3 support** (insufficient 1GB RAM for MediaPipe + Flask + OS)
- **USB webcam dependency** (Logitech C270 or compatible, 720p minimum)
- **Storage:** 16GB minimum SD card (32GB recommended), Class 10+ for performance
- **Memory:** 4GB minimum (8GB recommended for headroom)
- **Power:** 5V 3A minimum for stable operation (official Pi power supply)
- **Network:** WiFi 802.11n minimum or Ethernet (local network only, no internet required)

**Software Stack Constraints:**
- **OS:** Raspberry Pi OS (Debian-based) - full Linux, not microcontroller
- **Python:** 3.9+ required for MediaPipe compatibility
- **MediaPipe Pose:** Pre-trained models (~2GB), no GPU acceleration available
- **OpenCV:** Camera handling and frame processing
- **Flask:** Lightweight web server suitable for edge deployment
- **SQLite:** Embedded database (no separate server), WAL mode for durability
- **Pico CSS:** 7-9KB gzipped, zero build step, semantic HTML approach
- **systemd:** Service management for auto-start and crash recovery

**Architecture-Defining Constraints:**
- **Zero cloud dependencies:** Cannot offload compute or storage to external services (privacy mission-critical)
- **CPU-only processing:** All CV inference on ARM CPU drives model selection and FPS targets
- **Single-device architecture:** No distributed systems complexity, but also no horizontal scaling
- **Local network only:** No internet connectivity required for operation (update checks optional)
- **Limited computational budget:** Must maintain real-time performance within Pi resource envelope

**Critical Dependencies:**
- MediaPipe Pose library (Google) for landmark detection
- OpenCV for camera interface and frame manipulation
- Flask for web serving (lightweight, Python-native)
- SQLite for data persistence (serverless, embedded)
- systemd for service lifecycle management (Raspberry Pi OS standard)

### Cross-Cutting Concerns Identified

**1. Performance Optimization (Pervasive)**
- **Scope:** Affects CV pipeline, dashboard rendering, database queries, WebSocket updates
- **Constraint:** Pi 4/5 ARM CPU with no GPU acceleration
- **Implications:**
  - Frame rate throttling and resolution optimization in CV pipeline
  - Minimal CSS bundle (7-9KB Pico CSS chosen specifically)
  - Database query optimization with proper indexing
  - WebSocket message throttling to avoid UI lag
  - Memory profiling to prevent leaks during 8+ hour operation

**2. Privacy & Security (Architectural Foundation)**
- **Scope:** Entire system design, UI indicators, network binding, data storage
- **Constraint:** Zero external network traffic, 100% local processing
- **Implications:**
  - No external API calls during operation (blocks cloud analytics, crash reporting)
  - Network binding to local interfaces only (security by default)
  - Camera recording indicator always visible (UX trust requirement)
  - Pause/resume controls prominently accessible (user autonomy)
  - Optional encryption at rest for Pro tier (performance trade-off acceptable)

**3. Real-Time Data Flow (System-Wide)**
- **Scope:** CV pipeline → classification → storage → alert logic → WebSocket → UI
- **Constraint:** <100ms latency from posture change to UI update (NFR-P2)
- **Implications:**
  - Asynchronous processing pipeline to avoid blocking
  - WebSocket persistent connections for push updates
  - In-memory state management for current session
  - Database writes batched or async to avoid pipeline stalls
  - Event-driven architecture for alert triggering

**4. Reliability & Fault Tolerance (Always-On Operation)**
- **Scope:** Service lifecycle, camera handling, power loss, database integrity
- **Constraint:** 99%+ uptime, auto-recovery, 24/7 operation
- **Implications:**
  - systemd watchdog for automatic restart on crash
  - SQLite WAL mode for crash-resistant writes
  - Camera disconnect/reconnect detection and retry logic
  - Graceful degradation when camera unavailable
  - Logging and monitoring for troubleshooting

**5. Progressive Disclosure & Accessibility (UX-Driven)**
- **Scope:** Dashboard UI, settings configuration, onboarding flow
- **Constraint:** Support both Alex (high-tech) and Jordan (low-tech) user personas
- **Implications:**
  - Simple default UI with advanced settings hidden
  - Semantic HTML for screen reader support
  - Responsive design without mobile-first compromises
  - Colorblind-safe palette (green/amber, not red for bad posture)
  - Keyboard shortcuts for power users (optional)

**6. Extensibility & Open Source (Community Growth)**
- **Scope:** Plugin system, contribution workflow, API design
- **Constraint:** Solo developer initially, community contributions for growth
- **Implications:**
  - Clean architecture with separation of concerns
  - Documented APIs and plugin hooks (future)
  - Comprehensive CONTRIBUTING.md and development setup
  - CI/CD for automated testing of community PRs
  - Modular design to allow feature additions without core rewrites

**7. Data Lifecycle Management (Free vs Pro)**
- **Scope:** Storage, retention policies, data cleanup, Pro tier features
- **Constraint:** 7-day free, 30+ day Pro, performance with 1+ year data
- **Implications:**
  - Database partitioning or archival strategy for old data
  - Tier-aware queries (filter by date based on user tier)
  - Automatic cleanup jobs for free tier users
  - Migration path when users upgrade to Pro
  - Database schema designed for efficient date-range queries

## Starter Template Evaluation

### Primary Technology Domain

**IoT/Embedded Full-Stack System** based on project requirements analysis.

DeskPulse is a privacy-first edge computing system running on Raspberry Pi hardware with a web dashboard interface. Unlike typical web applications, the architectural constraints are driven by:
- Hardware limitations (Pi 4/5 ARM CPU, no GPU acceleration)
- Privacy requirements (100% local processing, zero cloud dependencies)
- Performance requirements (5-15 FPS real-time computer vision)
- Deployment model (single device, local network only, systemd service)

### Architectural Approach Decision

**Selected: Flask Application Factory Pattern with Blueprints**

**Rationale for Selection:**

While the PRD mentions "2-week MVP" and "solo developer" (which typically suggests starting simple), the Flask Application Factory pattern is chosen for critical strategic reasons:

**1. Testing Infrastructure Required (Week 2 Launch Criteria)**
- NFR-M2 requires 70%+ unit test coverage on core logic before public launch
- Factory pattern enables isolated test configurations without complex mocking
- CV pipeline (MediaPipe + OpenCV) requires unit tests with mock camera input
- Single-file architecture makes clean test isolation nearly impossible

**2. Community Contribution Strategy (FR53-FR60, Month 2-3 Success Metric)**
- PRD success criteria includes "15+ contributors by Month 3, 50+ by Month 12"
- 2025 Flask community consensus: Application factory is expected for serious projects
- Contributors recognize and trust this structure immediately
- Migration from single-file to factory pattern is painful and blocks contribution momentum

**3. Multiple Configuration Environments (Deployment Requirement)**
- **Development:** Pi desktop testing with debug logging, mock camera fallback
- **Production:** systemd service, optimized logging, real camera required
- **Testing:** Mock camera, no CV processing, in-memory database
- **CI/CD:** Automated test runs with simulated posture data
- Factory pattern handles environment switching natively via config classes

**4. Future Plugin System (Architectural Extensibility)**
- Month 2-3 features: phone detection (YOLOv8), gaze analysis, break reminders
- Blueprints enable modular feature additions without core rewrites
- Community can contribute plugins (custom alerts, integrations, analytics)
- Plugin architecture is core to open source growth strategy

**5. SocketIO Integration Complexity**
- Real-time WebSocket updates for multi-device dashboard (NFR-SC1: 10+ simultaneous connections)
- SocketIO requires proper app context initialization to avoid circular imports
- Factory pattern with `socketio.init_app(app)` solves this cleanly
- Single-file apps create import nightmares when adding WebSocket support

**6. Minimal Overhead for MVP (Time Investment Analysis)**
- Setup cost: 3 hours upfront structure
- Alternative cost: 2-3 days painful refactoring at Month 3 when contributors arrive
- Technical debt avoided: Circular imports, config hell, untestable code
- 2025 Flask best practice: Start with factory even for "small" projects

**Time Investment:** 3 hours upfront vs 2-3 days refactoring at Month 3 = Clear win for factory pattern.

### Project Structure

**DeskPulse Flask Application Factory Structure:**

```
deskpulse/
├── app/
│   ├── __init__.py              # create_app() factory function
│   ├── extensions.py            # socketio, db init (init_app pattern)
│   ├── config.py                # Config classes (Development, Testing, Production, Systemd)
│   │
│   ├── main/                    # Main blueprint (dashboard, health checks)
│   │   ├── __init__.py
│   │   ├── routes.py            # Dashboard HTTP endpoints
│   │   └── events.py            # SocketIO event handlers
│   │
│   ├── api/                     # API blueprint (future: mobile app, integrations)
│   │   ├── __init__.py
│   │   └── routes.py            # RESTful API endpoints
│   │
│   ├── posture/                 # Computer vision module (not a blueprint - pure logic)
│   │   ├── __init__.py
│   │   ├── capture.py           # Camera capture and frame handling
│   │   ├── detection.py         # MediaPipe Pose landmark detection
│   │   └── classification.py   # Binary good/bad posture logic
│   │
│   ├── alerts/                  # Alert management module
│   │   ├── __init__.py
│   │   └── manager.py           # Alert threshold logic, notification triggering
│   │
│   ├── data/                    # Data persistence module
│   │   ├── __init__.py
│   │   ├── database.py          # SQLite connection management (WAL mode)
│   │   └── models.py            # Data models (posture records, user settings)
│   │
│   ├── static/                  # Static assets (CSS, JavaScript, images)
│   │   ├── css/
│   │   │   └── pico.min.css     # Pico CSS 7-9KB bundle
│   │   ├── js/
│   │   │   └── dashboard.js     # SocketIO client, real-time UI updates
│   │   └── img/
│   │
│   └── templates/               # Jinja2 templates (semantic HTML)
│       ├── base.html            # Base template with Pico CSS
│       ├── dashboard.html       # Main dashboard view
│       └── settings.html        # Configuration UI
│
├── tests/                       # Test suite (pytest)
│   ├── conftest.py              # Test fixtures and app factory
│   ├── test_posture.py          # CV pipeline unit tests (mock camera)
│   ├── test_alerts.py           # Alert logic tests
│   ├── test_api.py              # API endpoint tests
│   └── test_integration.py      # End-to-end integration tests
│
├── migrations/                  # Database schema migrations (future)
│
├── scripts/                     # Utility scripts
│   ├── install.sh               # One-line installer (FR24)
│   └── systemd/
│       └── deskpulse.service    # systemd service file
│
├── run.py                       # Application entry point (development)
├── wsgi.py                      # WSGI entry point (production/systemd)
├── config.py                    # Top-level config loader
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Development dependencies (pytest, black, flake8)
└── README.md                    # Installation and setup documentation
```

### Architectural Decisions Provided by Factory Pattern

**Language & Runtime:**
- **Python 3.9+** (MediaPipe compatibility requirement)
- **Virtual environment:** venv or virtualenv for dependency isolation
- **Type hints:** Optional but recommended for maintainability (Python 3.9+ typing support)

**Application Factory Configuration:**

```python
# app/__init__.py
from flask import Flask
from app.extensions import socketio, init_db

def create_app(config_name='development'):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')

    # Initialize extensions
    init_db(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
```

**Extensions Pattern (Avoiding Circular Imports):**

```python
# app/extensions.py
from flask_socketio import SocketIO
import sqlite3

# Create extension instances outside factory
socketio = SocketIO()

def init_db(app):
    """Initialize SQLite database with WAL mode"""
    # Database initialization logic here
    # Uses app.config['DATABASE_PATH']
    pass
```

**Configuration Classes (Environment Management):**

```python
# app/config.py
import os

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE_PATH = os.path.join(os.getcwd(), 'data', 'deskpulse.db')
    CAMERA_DEVICE = 0  # /dev/video0
    POSTURE_ALERT_THRESHOLD = 600  # 10 minutes in seconds

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    MOCK_CAMERA = False  # Use real camera

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DATABASE_PATH = ':memory:'  # In-memory SQLite for tests
    MOCK_CAMERA = True  # Use mock camera for tests

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'INFO'
    # Production-specific optimizations

class SystemdConfig(ProductionConfig):
    LOG_LEVEL = 'WARNING'
    # systemd service-specific configuration
```

**Build Tooling:**
- **No build step required:** Flask serves static files directly
- **Development server:** Flask built-in development server (Werkzeug)
- **Production server:** Gunicorn or gevent (SocketIO compatibility)
- **systemd service:** Direct Python execution via `wsgi.py` entry point

**Testing Framework:**
- **pytest:** Test framework (industry standard for Python)
- **pytest-flask:** Flask-specific test fixtures
- **pytest-cov:** Code coverage reporting (NFR-M2: 70%+ target)
- **Mock camera fixtures:** Simulate video frames for CV pipeline testing
- **Factory pattern enables:** Isolated test app instances with test config

**Code Organization Patterns:**
- **Blueprints for HTTP routes:** Modular URL registration, future plugin support
- **Separate modules for logic:** CV pipeline, alerts, data persistence independent of web layer
- **Extensions pattern:** SocketIO, database init use `init_app()` to avoid circular imports
- **Config classes:** Environment-specific settings without code changes

**Development Experience:**
- **Hot reloading:** Flask development server auto-reloads on code changes
- **Debugging:** Flask debug mode with Werkzeug debugger
- **Logging:** Structured logging with Python logging module (NFR-M4)
- **Linting:** flake8 for PEP 8 compliance (NFR-M1: <10 violations per 1000 lines)
- **Formatting:** black for consistent code style
- **Type checking:** mypy (optional) for type hint validation

### SocketIO Integration Pattern (Critical for Real-Time Updates)

Based on 2025 Flask-SocketIO best practices, the recommended integration pattern:

```python
# app/extensions.py
from flask_socketio import SocketIO

# Create SocketIO instance outside factory
socketio = SocketIO()

# app/__init__.py
def create_app(config_name='development'):
    app = Flask(__name__)
    # ... load config, init db ...

    # Initialize SocketIO AFTER registering blueprints
    socketio.init_app(app, cors_allowed_origins="*")

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app

# app/main/events.py
from app.extensions import socketio
from flask_socketio import emit

@socketio.on('connect')
def handle_connect():
    emit('status', {'msg': 'Connected to DeskPulse'})
```

**Why This Matters:**
- Avoids `AttributeError: 'Blueprint' object has no attribute 'wsgi_app'`
- Enables event handlers in blueprint modules
- Supports multiple simultaneous WebSocket connections (NFR-SC1)

### Database Pattern (Lightweight SQLite without SQLAlchemy)

DeskPulse uses **direct SQLite connections** instead of SQLAlchemy for simplicity and performance on Pi hardware:

```python
# app/data/database.py
import sqlite3
from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Enable WAL mode for crash resistance (NFR-R3)
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    app.teardown_appcontext(close_db)
```

**Rationale:**
- SQLAlchemy ORM adds ~50MB memory overhead (significant on Pi 4GB RAM)
- Direct SQLite faster for simple queries (posture records are time-series data)
- WAL mode provides crash resistance without ORM complexity
- Easier for community contributors (no ORM learning curve)

### Implementation Roadmap

**Step 1: Project Initialization (Story 1, Week 1)**
```bash
# Create project structure
mkdir -p deskpulse/{app/{main,api,posture,alerts,data,static/{css,js,img},templates},tests,scripts/systemd}
cd deskpulse
python3 -m venv venv
source venv/bin/activate

# Install core dependencies
pip install flask flask-socketio python-socketio opencv-python mediapipe
pip install --dev pytest pytest-flask pytest-cov black flake8
```

**Step 2: Application Factory Setup (Story 1, Week 1)**
- Implement `create_app()` factory in `app/__init__.py`
- Configure extensions pattern in `app/extensions.py`
- Create config classes for dev/test/prod environments
- Set up `run.py` and `wsgi.py` entry points

**Step 3: Test Infrastructure (Story 2, Week 1)**
- Configure pytest with factory fixtures in `tests/conftest.py`
- Implement mock camera fixture for CV pipeline testing
- Verify test config uses in-memory database
- Validate test isolation (each test gets fresh app instance)

**Step 4: Core Module Development (Stories 3-8, Week 1-2)**
- CV pipeline module (`app/posture/`)
- Alert management module (`app/alerts/`)
- Data persistence module (`app/data/`)
- Dashboard blueprint (`app/main/`)
- SocketIO event handlers (`app/main/events.py`)

**Note:** Project initialization using this pattern should be **Story 1** in the first epic.

### Migration from Single-File (If Needed)

**Not applicable** - DeskPulse starts with application factory pattern from Day 1, avoiding migration pain entirely.

### Factory Pattern Validation Criteria

Before proceeding to implementation, verify the factory pattern meets these requirements:

✅ **Multiple config instances:** Can create app with dev/test/prod configs
✅ **Test isolation:** Each pytest creates fresh app instance with test config
✅ **Extension initialization:** SocketIO, database init without circular imports
✅ **Blueprint registration:** Routes organized by feature domain
✅ **Environment switching:** Config change via environment variable, no code modification
✅ **Contributor ready:** Structure recognizable to Flask community in 2025

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Database schema design (flexible with JSON metadata)
- CV processing thread model (multi-threaded architecture)
- Camera failure handling (graceful degradation + watchdog)
- Configuration management (INI files + environment variables)

**Important Decisions (Shape Architecture):**
- Alert notification delivery (hybrid native + browser)
- Logging infrastructure (systemd journal integration)

**Deferred Decisions (Post-MVP):**
- Plugin system architecture (Month 2-3, after community forms)
- Cloud backup mechanisms (Pro tier, optional privacy-preserving)
- Multi-user support (B2B features, Month 6+)
- Advanced analytics engine (pattern detection, Month 2-3)

### Data Architecture

**Decision: Database Schema Pattern**

**Selected: Flexible Schema with JSON Metadata Extensions**

```sql
CREATE TABLE posture_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    posture_state TEXT NOT NULL,  -- 'good' or 'bad'
    user_present BOOLEAN DEFAULT 1,
    confidence_score REAL,  -- MediaPipe confidence for threshold tuning
    metadata JSON  -- Extensible: pain_level, phone_detected, focus_metrics
);
CREATE INDEX idx_timestamp ON posture_events(timestamp);
CREATE INDEX idx_posture_state ON posture_events(posture_state);
```

**Rationale:**
- **Avoids migration pain:** SQLite's "12-step procedure" for adding columns avoided entirely
- **Phased feature support:** Week 1 (basic tracking) → Week 2 (pain levels via `metadata.pain_level`) → Month 2-3 (phone detection via `metadata.phone_detected`)
- **MediaPipe confidence logging:** Critical for debugging false positives and threshold tuning
- **JSON performance:** SQLite's JSON1 extension (native in Python sqlite3) handles small metadata efficiently
- **Storage impact:** ~50 bytes/row overhead = 25MB per million events (negligible for Pi storage)

**JSON Query Examples:**
```python
# Python: Store metadata
metadata = {"pain_level": 3, "confidence": 0.87}
cursor.execute(
    "INSERT INTO posture_events (timestamp, posture_state, metadata) VALUES (?, ?, ?)",
    (datetime.now(), 'bad', json.dumps(metadata))
)

# SQL: Query metadata
SELECT timestamp, json_extract(metadata, '$.pain_level') as pain
FROM posture_events
WHERE date(timestamp) = date('now');
```

**Pain Tracking Metadata Schema (Week 2 Feature - FR20):**

The `metadata` JSON column uses a structured schema for pain tracking:

```python
# Pain tracking metadata structure
pain_metadata = {
    "pain_level": int,      # Required: 1-10 scale (validated)
    "pain_location": str,   # Optional: "neck" | "back" | "shoulders" | "other"
    "note": str            # Optional: free-text user comment (max 500 chars)
}

# Example usage:
metadata = {
    "pain_level": 7,
    "pain_location": "neck",
    "note": "Increased pain after 2-hour coding session"
}

# Validation rules enforced in application layer:
# - pain_level: Must be integer 1-10 (inclusive)
# - pain_location: Must be one of allowed values if provided
# - note: Max 500 characters, sanitized for XSS before display
# - Unknown keys are preserved but ignored by analytics

# Query for pain trend analysis:
SELECT
    date(timestamp) as day,
    AVG(json_extract(metadata, '$.pain_level')) as avg_pain,
    json_extract(metadata, '$.pain_location') as location,
    COUNT(*) as entries_with_pain
FROM posture_event
WHERE json_extract(metadata, '$.pain_level') IS NOT NULL
GROUP BY day, location
ORDER BY day DESC
LIMIT 7;
```

**Week 2 Integration:**
- Pain tracking UI added to dashboard (modal or sidebar)
- User can optionally log pain level when alert triggers
- Analytics correlate pain levels with posture patterns
- Dashboard shows pain trends alongside posture improvement

**Affects:** FR14-FR23 (Analytics & Reporting), FR20 (pain tracking), Month 2-3 features

---

### Real-Time Processing Architecture

**Decision: CV Processing Thread Model**

**Selected: Multi-Threaded Architecture with Dedicated CV Thread**

**Architecture:**
```python
# Dedicated CV processing thread
cv_queue = queue.Queue(maxsize=1)  # Latest state only
cv_thread = threading.Thread(target=cv_pipeline_loop, daemon=True)
cv_thread.start()

# Flask/SocketIO on main thread
socketio = SocketIO(app, async_mode='threading')

# CV thread writes to queue
def cv_pipeline_loop():
    while True:
        ret, frame = cap.read()
        # MediaPipe processing...
        cv_queue.put({
            'state': 'bad',
            'timestamp': now,
            'confidence': 0.87
        })

# Flask/SocketIO thread reads and emits
@socketio.on('connect')
def stream_updates():
    while True:
        data = cv_queue.get()
        emit('posture_update', data)
```

**Rationale:**
- **Flask-SocketIO 2025 recommendation:** Threading is now official production recommendation (eventlet "winding down", gevent compatibility issues)
- **OpenCV/MediaPipe release GIL:** Numpy operations and C/C++ processing achieve true parallelism during CV inference
- **Pi 4/5 multi-core support:** 4 cores allow CV thread dedicated CPU time even with Python GIL
- **Queue overhead negligible:** <1ms vs 100-200ms CV processing time
- **Meets NFR-P2:** <100ms latency from posture change to UI update (queue + emit = ~6-11ms)

**Alternative Rejected:**
- **gevent/eventlet (Option A):** Monkey-patching breaks MediaPipe's blocking operations, compatibility issues
- **multiprocessing (Option C):** Overkill complexity, 20-50ms serialization overhead, harder debugging, GIL not the bottleneck

**Dependencies:**
- `flask-socketio` with `async_mode='threading'`
- Python `queue.Queue` (stdlib)
- `threading` module (stdlib)

**Affects:** FR1-FR7 (Posture Monitoring), FR35-FR45 (Dashboard & Visualization), NFR-P1, NFR-P2

---

### Alert & Notification System

**Decision: Desktop Notification Mechanism**

**Selected: Hybrid Native + Browser Notifications**

**Architecture:**
```python
# Primary: libnotify (native Linux notifications)
import subprocess
subprocess.run(['notify-send', 'DeskPulse', 'Bad posture detected for 10 minutes'])

# Also emit via SocketIO for browser fallback
socketio.emit('posture_alert', {'message': 'Bad posture detected for 10 minutes'})
```

```javascript
// Browser: Request permission once, show when granted
if ('Notification' in window) {
    Notification.requestPermission();
}

socketio.on('posture_alert', (data) => {
    if (Notification.permission === 'granted') {
        new Notification('DeskPulse', {body: data.message});
    }
});
```

**Rationale:**
- **Primary use case coverage:** libnotify for users at Pi desktop (native, zero Python dependencies)
- **Multi-device support:** Browser notifications for remote dashboard access (laptop/phone checking Pi's dashboard)
- **Progressive enhancement:** Graceful degradation pattern - try native, fallback to browser
- **Do Not Disturb respect:** libnotify honors Pi OS notification settings automatically
- **Implementation time:** ~20 minutes to add browser notifications on top of libnotify

**Coverage Matrix:**
- **User at Pi desk:** libnotify notification
- **Remote browser user:** Web Notification API
- **Dashboard closed:** No notification (acceptable - user intentionally left)

**Dependencies:**
- `libnotify-bin` (pre-installed on Raspberry Pi OS Desktop)
- Browser Notification API (Web standard, no dependencies)

**Affects:** FR8-FR13 (Alert & Notification System), NFR-SC1 (multi-device dashboard)

---

### Reliability & Fault Tolerance

**Decision: Camera Failure Handling Strategy**

**Selected: Hybrid Graceful Degradation + systemd Watchdog Safety Net**

**Layer 1: Graceful Degradation (Fast Recovery)**
```python
# CV thread with 3-state machine
camera_state = 'connected'  # 'connected', 'degraded', 'disconnected'

while True:
    try:
        ret, frame = cap.read()
        if not ret:
            camera_state = 'degraded'
            socketio.emit('camera_status', {'state': 'degraded'})

            # Quick retry loop - 3 attempts, ~2-3 seconds total
            for i in range(3):
                cap.release()
                cap = cv2.VideoCapture(CAMERA_DEVICE)
                ret, frame = cap.read()
                if ret:
                    camera_state = 'connected'
                    socketio.emit('camera_status', {'state': 'connected'})
                    break
            else:
                # All retries failed
                camera_state = 'disconnected'
                socketio.emit('camera_status', {'state': 'disconnected'})
                time.sleep(10)  # Wait before full reconnect attempt

    except Exception as e:
        logging.error(f"Camera exception: {e}")
        # Continue retry logic
```

**Layer 2: systemd Watchdog (Safety Net)**
```python
# Send watchdog ping every 15 seconds
import sdnotify
notifier = sdnotify.SystemdNotifier()
notifier.notify("READY=1")

# Inside CV loop
if time.time() - last_watchdog > 15:
    notifier.notify("WATCHDOG=1")
    last_watchdog = time.time()
```

```ini
# /etc/systemd/system/deskpulse.service
[Service]
Type=notify
WatchdogSec=30
Restart=on-failure
RestartSec=10
```

**Rationale:**
- **USB camera reality:** Transient glitches (power fluctuations, USB bus resets) on Pi resolve in 1-3 retries without full service restart
- **Meets NFR-R4:** 3 quick retries (~2-3 sec) + 10 sec reconnect = <10 seconds camera recovery
- **Dashboard visibility:** Users see real-time camera status ('connected'/'degraded'/'disconnected') via SocketIO
- **Preserves session state:** In-memory data maintained during transient failures, no data loss
- **Safety net:** systemd watchdog (30 sec timeout) restarts service on true Python crashes or infinite loops
- **Watchdog timing:** 30 sec > 10 sec reconnect cycle to avoid false-positive restarts during legitimate recovery

**Coverage:**
- **Transient USB failures:** Layer 1 recovers in 2-3 seconds
- **Permanent camera disconnect:** Layer 1 signals 'disconnected', retries every 10 sec
- **Python crash/hang:** Layer 2 systemd restarts service after 30 sec

**Dependencies:**
- `sdnotify` Python package for systemd watchdog integration
- systemd service configuration

**Affects:** FR6 (camera disconnect detection), NFR-R1 (99%+ uptime), NFR-R4 (10 sec reconnection)

---

### Configuration Management

**Decision: Configuration Storage & Environment Switching**

**Selected: INI Config File + Environment Variables for Secrets**

**Configuration Hierarchy:**
```ini
# System defaults: /etc/deskpulse/config.ini.example
[camera]
device = 0
resolution = 720p
fps_target = 10

[alerts]
posture_threshold_minutes = 10
notification_enabled = true

[dashboard]
port = 5000
update_interval_seconds = 2

[security]
secret_key = ${DESKPULSE_SECRET_KEY}  # Loaded from environment variable
```

```ini
# User overrides: ~/.config/deskpulse/config.ini
[camera]
device = 1  # Override: use /dev/video1

[alerts]
posture_threshold_minutes = 15  # Override: 15 min threshold
```

**Python Config Loading:**
```python
# app/config.py
import os
import configparser

config = configparser.ConfigParser()
config.read([
    '/etc/deskpulse/config.ini',  # System defaults
    os.path.expanduser('~/.config/deskpulse/config.ini')  # User overrides
])

class Config:
    CAMERA_DEVICE = int(config.get('camera', 'device', fallback='0'))
    ALERT_THRESHOLD = int(config.get('alerts', 'posture_threshold_minutes', fallback='10')) * 60
    SECRET_KEY = os.environ.get('DESKPULSE_SECRET_KEY', 'dev-key-insecure')
```

**systemd Service Environment:**
```ini
# /etc/systemd/system/deskpulse.service
[Service]
Environment="DESKPULSE_SECRET_KEY=generated-at-install-time"
EnvironmentFile=-/etc/deskpulse/secrets.env
```

**Rationale:**
- **User-friendly:** INI format editable by non-technical users (Alex, Maya, Jordan personas)
- **Self-service troubleshooting:** Aligns with FR58 (80%+ issues resolvable via documentation) - users can adjust camera device, thresholds, ports without developer intervention
- **Secrets security:** Environment variables for `SECRET_KEY`, never in user-editable files
- **Multi-environment support:** System defaults + user overrides pattern (later files override earlier)
- **Linux conventions:** Follows XDG Base Directory spec (`~/.config/`), familiar to Pi users
- **Sane defaults:** Ships with working `/etc/deskpulse/config.ini.example`, users copy and customize

**Alternative Rejected:**
- **Environment variables only (Option A):** Nightmare UX - "How do I change camera?" requires systemd environment file editing
- **Python settings.py (Option C):** Forces users to write Python syntax, typos break app, too technical

**Affects:** FR24, FR31 (configuration management), NFR-U1, NFR-U2 (installation and self-service)

---

### Logging & Observability

**Decision: Logging Strategy for 24/7 Operation**

**Selected: systemd Journal Integration**

**Implementation:**
```python
# app/__init__.py
import logging
import systemd.journal

def create_app(config_name='development'):
    app = Flask(__name__)

    # Configure logging to systemd journal
    handler = systemd.journal.JournalHandler()
    handler.setFormatter(logging.Formatter(
        '[%(levelname)s] %(name)s: %(message)s'
    ))

    # Set log level from config
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.root.setLevel(log_level)
    logging.root.addHandler(handler)

    return app
```

**Access Patterns:**
```bash
# Live tail logs
journalctl -u deskpulse -f

# Last 100 lines
journalctl -u deskpulse -n 100

# Logs since boot
journalctl -u deskpulse -b

# Logs from specific time range
journalctl -u deskpulse --since "2025-12-01" --until "2025-12-05"

# Filter by priority (errors only)
journalctl -u deskpulse -p err
```

**Rationale:**
- **Native systemd integration:** Logs automatically associated with `deskpulse.service` unit
- **Automatic rotation:** journald handles disk space management, no manual logrotate configuration
- **Structured metadata:** journald stores log level, timestamp, process ID automatically
- **No file management:** Zero disk usage concerns, journald vacuum policies handle cleanup
- **Pi OS standard:** journalctl is standard tool on Raspberry Pi OS, users already familiar
- **Meets NFR-M4:** Structured logging with timestamps, severity, context

**Log Levels by Environment:**
```python
# Development: DEBUG (verbose CV pipeline details)
# Testing: DEBUG (test execution visibility)
# Production: INFO (normal operations, alerts, camera status)
# Systemd: WARNING (errors only, reduce SD card wear)
```

**Dependencies:**
- `systemd-python` package for `JournalHandler`

**Alternative Rejected:**
- **File-based logging (Option B):** Requires manual logrotate setup, separate from systemd tooling
- **Hybrid (Option C):** Duplicate logs waste disk space, unnecessary complexity

**Affects:** NFR-M4 (structured logging), FR33 (operational event logging), troubleshooting

---

### Decision Impact Analysis

**Implementation Sequence:**

1. **First (Week 1 Setup):**
   - Database schema creation (flexible JSON pattern)
   - Configuration management (INI files + env vars)
   - Logging infrastructure (systemd journal)

2. **Second (Week 1 Core):**
   - Multi-threaded CV pipeline architecture
   - Camera failure handling (graceful degradation)

3. **Third (Week 1 Features):**
   - Alert notification system (hybrid native + browser)
   - systemd watchdog integration

**Cross-Component Dependencies:**

- **CV Thread → Database:** CV thread writes posture events directly to SQLite via queue consumer
- **CV Thread → SocketIO:** Real-time posture updates emitted via shared queue
- **Camera Handling → Dashboard:** Camera status ('connected'/'degraded'/'disconnected') emitted via SocketIO for UI indicator
- **Alert System → Configuration:** Threshold values loaded from INI config, adjustable by users
- **Logging → All Components:** systemd journal handler shared across CV pipeline, Flask routes, alert system
- **systemd Watchdog → CV Thread:** Watchdog pings sent from CV processing loop to verify liveness

**Architectural Cohesion:**

All decisions support the core mission: **Privacy-first, edge-computing posture monitoring with 24/7 reliability on Raspberry Pi hardware.**

- **Privacy:** 100% local processing (multi-threaded isolation), zero external dependencies, local config files
- **Reliability:** Layered fault tolerance (graceful degradation + watchdog), automatic recovery, structured logging
- **Performance:** Dedicated CV thread, GIL-released operations, minimal overhead (<100ms latency)
- **Usability:** User-friendly INI config, hybrid notifications, real-time dashboard status
- **Extensibility:** JSON metadata field, blueprint architecture, community-ready structure

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 21 areas where AI agents or contributors could make incompatible choices without standardization.

**Conflict Categories:**
- **Naming Conflicts (9):** Database tables/columns, Python functions/classes, API endpoints, SocketIO events, files, config keys, JSON fields, logs, tests
- **Structure Conflicts (5):** Test location, utility modules, template organization, static assets, config files
- **Format Conflicts (4):** API responses, SocketIO payloads, date/time formats, error structures
- **Process Conflicts (3):** Exception handling, logging formats, state updates

**Resolution:** All 21 conflict points resolved through standardized patterns below.

---

### Naming Patterns

#### Python Naming Conventions (PEP 8 Strict)

**All Python code MUST follow PEP 8 without modifications.**

**Rules:**
- **Functions/Variables:** `snake_case` (e.g., `get_posture_state()`, `camera_device`, `retry_count`)
- **Classes:** `PascalCase` (e.g., `PostureClassifier`, `CameraHandler`, `AlertManager`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `CAMERA_DEVICE`, `ALERT_THRESHOLD`, `MAX_RETRIES`)
- **Modules/Files:** `snake_case` (e.g., `posture_monitor.py`, `camera_handler.py`, `alert_manager.py`)
- **Private Methods:** Leading underscore `_method_name()` (e.g., `_calculate_confidence()`, `_retry_connection()`)

**Configuration:**
```ini
# .flake8
[flake8]
max-line-length = 100  # Not 79 (modern screens, Pi development environment)
ignore = E203,W503     # Black formatter conflicts
```

**Enforcement:**
- **Black formatter:** Auto-format on save, pre-commit hook
- **Flake8 linter:** CI/CD pipeline check, <10 violations per 1000 lines (NFR-M1)

**Good Examples:**
```python
class PostureClassifier:
    GOOD_POSTURE_THRESHOLD = 0.7

    def classify_posture(self, landmarks):
        confidence_score = self._calculate_confidence(landmarks)
        return 'good' if confidence_score > self.GOOD_POSTURE_THRESHOLD else 'bad'

    def _calculate_confidence(self, landmarks):
        """Private helper method for confidence calculation."""
        pass
```

**Anti-Patterns (NEVER use):**
```python
# WRONG: camelCase for functions/variables
def classifyPosture(landmarks):
    confidenceScore = calculateConfidence(landmarks)

# WRONG: snake_case for classes
class posture_classifier:
    pass

# WRONG: lowercase for constants
camera_device = 0  # Should be CAMERA_DEVICE
```

---

#### Database Naming Conventions

**SQLite schema MUST follow these rules:**

**Tables:**
- **Singular snake_case:** `posture_event`, `user_setting`, `alert_log` (NOT plural)
- **Rationale:** Each row = one entity, Django ORM standard, natural query reads

**Columns:**
- **snake_case:** `posture_state`, `timestamp`, `user_present`, `confidence_score`
- **Matches Python naming:** No camelCase/PascalCase friction

**Indexes:**
- **Format:** `idx_{table}_{column(s)}` (e.g., `idx_posture_event_timestamp`, `idx_posture_event_state`)
- **Multi-column:** `idx_{table}_{col1}_{col2}` (e.g., `idx_posture_event_timestamp_state`)

**Booleans:**
- **No `is_` prefix:** Use descriptive name (`user_present`, `notification_enabled`)
- **NOT:** `is_user_present`, `is_enabled`

**Example Schema:**
```sql
CREATE TABLE posture_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    posture_state TEXT NOT NULL,
    user_present BOOLEAN DEFAULT 1,
    confidence_score REAL,
    metadata JSON
);

CREATE INDEX idx_posture_event_timestamp ON posture_event(timestamp);
CREATE INDEX idx_posture_event_state ON posture_event(posture_state);

CREATE TABLE user_setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

#### API & SocketIO Naming Conventions

**REST Endpoints:**
- **Resource naming:** Plural snake_case (`/api/events`, `/api/settings`)
- **Route parameters:** Flask format `<int:event_id>`, `<string:setting_key>`
- **Query parameters:** snake_case (`?start_date=2025-12-01&end_date=2025-12-06`)

**SocketIO Events:**
- **Event names:** snake_case with underscore separator
  - `posture_update`, `camera_status`, `alert_triggered`, `config_changed`
- **NOT:** dot notation (`posture.update`), camelCase (`postureUpdate`), kebab-case (`posture-update`)

**JSON Payloads:**
- **All keys:** snake_case to match Python/SQL naming
- **Consistency:** No mixing camelCase/snake_case within same payload

**Good Examples:**
```python
# REST endpoint
@api_bp.route('/api/events/<int:event_id>')
def get_event(event_id):
    event = query_event(event_id)
    if not event:
        raise NotFoundException('Event')
    return jsonify({
        'id': event.id,
        'posture_state': event.posture_state,
        'timestamp': event.timestamp.isoformat(),
        'confidence_score': event.confidence_score
    })

# SocketIO event
@socketio.on('connect')
def handle_connect():
    emit('posture_update', {
        'posture_state': 'bad',
        'timestamp': datetime.now().isoformat(),
        'confidence_score': 0.87,
        'user_present': True
    })
```

**Anti-Patterns:**
```python
# WRONG: Singular REST resource
@api_bp.route('/api/event/<int:id>')  # Should be /api/events/<int:event_id>

# WRONG: camelCase in JSON
return jsonify({'postureState': 'good', 'confidenceScore': 0.9})

# WRONG: Mixed naming conventions
return jsonify({'posture_state': 'good', 'confidenceScore': 0.9})  # Inconsistent!
```

---

### Format Patterns

#### API Response Formats

**Direct Response (No Wrapper)**

All API responses MUST use direct format without success/error wrappers.

**Success Response:**
```python
# Good: Direct data return
return jsonify({
    'posture_state': 'good',
    'timestamp': '2025-12-06T14:30:00Z',
    'confidence_score': 0.87
})

# Bad: Wrapped response (adds overhead)
return jsonify({
    'success': True,
    'data': {'posture_state': 'good', ...}
})
```

**Error Response:**
```python
# Standard error format
return jsonify({
    'error': 'Human-readable error message',
    'code': 'ERROR_CODE_CONSTANT'
}), status_code

# Examples
return jsonify({'error': 'Event not found', 'code': 'NOT_FOUND'}), 404
return jsonify({'error': 'Database connection failed', 'code': 'DB_CONNECTION_FAILED'}), 500
```

**Date/Time Format:**
- **ISO 8601 strings ONLY:** `2025-12-06T14:30:00Z` or `2025-12-06T14:30:00+00:00`
- **NOT Unix timestamps:** Harder to debug, less human-readable
- **Python serialization:** `datetime.isoformat()` or `datetime.strftime('%Y-%m-%dT%H:%M:%SZ')`

**Rationale:**
- **Performance:** Minimal payload size for Pi constraints
- **Debuggability:** ISO dates human-readable in logs/JSON
- **JavaScript-friendly:** `new Date(isoString)` works natively

---

#### Error Code Standards

**Standard Error Codes (ALL CAPS snake_case):**

**Camera Errors:**
- `CAMERA_NOT_FOUND` - Camera device not detected at initialization
- `CAMERA_DISCONNECTED` - Camera lost connection during operation
- `CAMERA_DEGRADED` - Camera experiencing transient failures (retry in progress)
- `CAMERA_ERROR` - General camera operation failure

**Database Errors:**
- `DB_ERROR` - General database operation failure
- `DB_CONNECTION_FAILED` - Cannot establish database connection
- `DB_INTEGRITY_ERROR` - Data integrity violation (unique constraint, etc.)

**Resource Errors:**
- `NOT_FOUND` - Requested resource does not exist (404)
- `INVALID_REQUEST` - Malformed request data (400)
- `UNAUTHORIZED` - Authentication required (401)
- `FORBIDDEN` - Insufficient permissions (403)

**System Errors:**
- `INTERNAL_ERROR` - Unexpected server error (500)
- `SERVICE_UNAVAILABLE` - Service temporarily unavailable (503)

**Usage:**
```python
# In API routes
if not event:
    raise NotFoundException('Event')

# In exception classes
class CameraException(DeskPulseException):
    def __init__(self, message):
        super().__init__(message, 'CAMERA_ERROR', 500)
```

---

### Process Patterns

#### Error Handling Patterns

**Flask Error Handlers (DRY Principle)**

**Custom Exception Hierarchy:**
```python
# app/exceptions.py
class DeskPulseException(Exception):
    """Base exception with error code and HTTP status"""
    def __init__(self, message, code, status_code=500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class CameraException(DeskPulseException):
    def __init__(self, message):
        super().__init__(message, 'CAMERA_ERROR', 500)

class NotFoundException(DeskPulseException):
    def __init__(self, resource):
        super().__init__(f'{resource} not found', 'NOT_FOUND', 404)

class DatabaseException(DeskPulseException):
    def __init__(self, message):
        super().__init__(message, 'DB_ERROR', 500)
```

**Global Error Handlers:**
```python
# app/__init__.py
from app.exceptions import DeskPulseException

@app.errorhandler(DeskPulseException)
def handle_deskpulse_error(e):
    logging.error(f"{e.code}: {e.message}")
    return jsonify({'error': e.message, 'code': e.code}), e.status_code

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({'error': 'Resource not found', 'code': 'NOT_FOUND'}), 404

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    logging.exception(f"Unexpected error: {e}")
    return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
```

**Simplified Route Code:**
```python
# Flask routes - clean and simple
@api_bp.route('/api/events/<int:event_id>')
def get_event(event_id):
    event = get_event_from_db(event_id)
    if not event:
        raise NotFoundException('Event')  # Error handler formats response
    return jsonify(event)
```

**CV Pipeline Exception Handling (Granular Control):**
```python
# CV thread - NEVER crash, always degrade gracefully
def cv_pipeline_loop():
    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                camera_state = 'degraded'
                # Quick retry logic (3 attempts)
                for i in range(3):
                    cap.release()
                    cap = cv2.VideoCapture(CAMERA_DEVICE)
                    ret, frame = cap.read()
                    if ret:
                        camera_state = 'connected'
                        break
                else:
                    camera_state = 'disconnected'
                    time.sleep(10)
                    continue

            # Process frame...

        except CameraException as e:
            logger.warning(f"Camera error: {e}")
            camera_state = 'degraded'
            # Continue loop, emit status via SocketIO
        except Exception as e:
            logger.exception(f"CV pipeline error: {e}")
            # Don't crash - emit error status, continue monitoring
```

**Rationale:**
- **Flask routes:** DRY principle via error handlers, clean business logic
- **CV pipeline:** Explicit exception handling, never crash 24/7 monitoring thread

---

#### Logging Format Standards

**Python Logger Hierarchy (NOT Manual Prefixes)**

**Logger Naming:**
```python
# In each module - use hierarchical logger names
import logging

# app/posture/detection.py
logger = logging.getLogger('deskpulse.cv')

# app/data/database.py
logger = logging.getLogger('deskpulse.db')

# app/alerts/manager.py
logger = logging.getLogger('deskpulse.alert')

# app/main/routes.py
logger = logging.getLogger('deskpulse.api')

# app/main/events.py
logger = logging.getLogger('deskpulse.socket')
```

**Standard Logger Names:**
- `deskpulse.cv` - Computer vision pipeline
- `deskpulse.db` - Database operations
- `deskpulse.alert` - Alert system
- `deskpulse.api` - Flask HTTP routes
- `deskpulse.socket` - SocketIO events
- `deskpulse.config` - Configuration loading
- `deskpulse.system` - systemd/service lifecycle

**Global Logging Configuration:**
```python
# app/__init__.py
import logging
import systemd.journal

def create_app(config_name='development'):
    app = Flask(__name__)

    # Configure logging format (applies to ALL loggers)
    handler = systemd.journal.JournalHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    logging.root.setLevel(log_level)
    logging.root.addHandler(handler)

    return app
```

**Output Format:**
```
2025-12-06 14:30:15 [deskpulse.cv] INFO: Camera connected: /dev/video0
2025-12-06 14:30:42 [deskpulse.cv] WARNING: Camera degraded: retrying (attempt 2/3)
2025-12-06 14:31:10 [deskpulse.db] ERROR: Write failed: disk full
2025-12-06 14:31:45 [deskpulse.alert] INFO: Alert triggered: bad posture 10 minutes
```

**Log Level Usage:**
- **ERROR:** Unrecoverable failures requiring immediate attention (camera completely failed, DB corruption, service crash)
- **WARNING:** Recoverable issues (camera degraded/retrying, slow queries, config issues)
- **INFO:** Normal operations (camera connected, alert sent, daily report generated, user config changed)
- **DEBUG:** Detailed diagnostic info (frame processing times, MediaPipe confidence scores, queue depths) - Dev/Test only

**Structured Logging (Optional Enhancement):**
```python
logger.info(
    "Posture changed: state=%s confidence=%.2f",
    state, confidence,
    extra={'event_type': 'posture_change', 'user_present': user_present}
)
```

**Rationale:**
- **Standard Python:** Every Python developer recognizes this pattern
- **Filterable:** `journalctl -u deskpulse | grep 'deskpulse.cv'` works perfectly
- **No typos:** Logger names checked at runtime, not manual `[CV]` strings
- **Hierarchical control:** Set `deskpulse.cv` to DEBUG while keeping `deskpulse.db` at INFO
- **One format change:** Adjust format string once in `create_app()`, affects all loggers

---

### Structure Patterns

#### Test Organization

**Test Location:**
- **Separate `tests/` directory** (pytest standard, Flask factory pattern)
- **NOT co-located** with application modules

**Project Structure:**
```
deskpulse/
├── app/
│   ├── posture/
│   │   ├── detection.py
│   │   └── classification.py
│   └── alerts/
│       └── manager.py
└── tests/
    ├── conftest.py          # pytest fixtures (app factory, mock camera)
    ├── test_posture.py       # Tests for app/posture/*
    ├── test_alerts.py        # Tests for app/alerts/*
    ├── test_api.py           # Tests for app/main/routes.py
    └── test_integration.py   # End-to-end integration tests
```

**Test File Naming:**
- **Format:** `test_{module}.py` (e.g., `test_posture.py`, `test_camera_handler.py`)
- **Matches module name** for easy mapping

**Test Function Naming:**
- **Format:** `test_{function}_{scenario}()` (e.g., `test_classify_posture_good_state()`, `test_camera_reconnect_on_failure()`)
- **Descriptive:** Function + scenario makes test intent clear

**Example:**
```python
# tests/test_posture.py
import pytest
from app.posture.classification import PostureClassifier

def test_classify_posture_good_state():
    """Test posture classification returns 'good' for high confidence."""
    classifier = PostureClassifier()
    result = classifier.classify_posture(landmarks=mock_good_landmarks)
    assert result == 'good'

def test_classify_posture_bad_state():
    """Test posture classification returns 'bad' for low confidence."""
    classifier = PostureClassifier()
    result = classifier.classify_posture(landmarks=mock_bad_landmarks)
    assert result == 'bad'

def test_classify_posture_user_absent():
    """Test posture classification handles user absence gracefully."""
    classifier = PostureClassifier()
    result = classifier.classify_posture(landmarks=None)
    assert result is None
```

---

#### Static Asset Organization

**Standard Structure:**
```
app/static/
├── css/
│   └── pico.min.css       # Pico CSS 7-9KB bundle (CDN fallback in production)
├── js/
│   └── dashboard.js       # SocketIO client, real-time UI updates
└── img/
    ├── logo.png
    └── favicon.ico
```

**Template Organization:**
```
app/templates/
├── base.html              # Base template with Pico CSS, common layout
├── dashboard.html         # Main dashboard view (extends base.html)
└── settings.html          # Configuration UI (extends base.html)
```

**Rationale:**
- **Flat structure:** Only 3 templates, no need for nested directories
- **Minimal JS:** Single `dashboard.js` file handles SocketIO + UI updates
- **No build step:** Static files served directly by Flask

---

### Enforcement Guidelines

**All AI Agents and Contributors MUST:**

1. **Follow PEP 8 strictly** - Enforced by Black formatter + Flake8 linter in CI/CD
2. **Use Python logger hierarchy** - `logging.getLogger('deskpulse.{component}')` NOT manual prefixes
3. **Use Flask error handlers** - Raise custom exceptions, let error handlers format responses
4. **Return ISO 8601 dates** - `datetime.isoformat()` in all JSON responses
5. **Name database tables singular snake_case** - `posture_event`, NOT `posture_events` or `PostureEvent`
6. **Use snake_case for all JSON keys** - Match Python/SQL naming conventions
7. **Place tests in `tests/` directory** - Separate from application code
8. **Never crash CV pipeline thread** - Graceful degradation with logging, continue monitoring
9. **Document new error codes** - Add to standard error code list in this document
10. **Log structured context** - Use logger hierarchy, include relevant context in messages

**Pattern Enforcement:**

**Pre-Commit Hooks:**
```bash
# .git/hooks/pre-commit
black app/ tests/
flake8 app/ tests/
pytest tests/ -v
```

**CI/CD Pipeline:**
```yaml
# GitHub Actions - lint and test on every PR
- name: Lint with flake8
  run: flake8 app/ tests/ --count --show-source --statistics

- name: Format check with Black
  run: black --check app/ tests/

- name: Run pytest
  run: pytest tests/ --cov=app --cov-report=term-missing
```

**Pattern Violation Process:**
1. **CI/CD fails** - PR cannot merge if linting/tests fail
2. **Code review** - Maintainer identifies pattern violations in PR review
3. **Update documentation** - If pattern needs modification, update this architecture document first
4. **Enforce consistently** - Apply same standards to all contributors (human and AI)

---

### Pattern Examples

**Good Example (All Patterns Applied):**
```python
# app/posture/classification.py
import logging
from app.exceptions import CameraException

logger = logging.getLogger('deskpulse.cv')

class PostureClassifier:
    """Classifies posture state from MediaPipe landmarks."""

    GOOD_POSTURE_THRESHOLD = 0.7

    def classify_posture(self, landmarks):
        """
        Classify posture as 'good' or 'bad' based on landmark confidence.

        Args:
            landmarks: MediaPipe pose landmarks or None if user absent

        Returns:
            str: 'good', 'bad', or None if user absent
        """
        if landmarks is None:
            logger.debug("No landmarks detected: user absent")
            return None

        try:
            confidence_score = self._calculate_confidence(landmarks)
            posture_state = 'good' if confidence_score > self.GOOD_POSTURE_THRESHOLD else 'bad'

            logger.info(
                "Posture classified: state=%s confidence=%.2f",
                posture_state, confidence_score
            )
            return posture_state

        except Exception as e:
            logger.exception("Posture classification failed: %s", e)
            raise CameraException(f"Classification error: {e}")

    def _calculate_confidence(self, landmarks):
        """Calculate confidence score from landmarks."""
        # Implementation...
        pass
```

**Anti-Pattern Example (Violations Highlighted):**
```python
# WRONG: Multiple pattern violations
import logging

log = logging.getLogger(__name__)  # WRONG: Should use 'deskpulse.cv'

class postureClassifier:  # WRONG: Should be PascalCase
    goodPostureThreshold = 0.7  # WRONG: Should be UPPER_SNAKE_CASE constant

    def classifyPosture(self, landmarks):  # WRONG: Should be snake_case
        if landmarks is None:
            log.info("[CV] No landmarks")  # WRONG: Manual prefix, not logger hierarchy
            return None

        confidenceScore = self.calculateConfidence(landmarks)  # WRONG: camelCase variable
        return 'good' if confidenceScore > self.goodPostureThreshold else 'bad'
```

---

### Pattern Summary

**21 Conflict Points Resolved:**

✅ Python naming (PEP 8 strict, 100-char lines, Black + Flake8)
✅ Database tables (singular snake_case)
✅ Database columns (snake_case, no `is_` prefix)
✅ Database indexes (`idx_{table}_{columns}`)
✅ REST endpoints (plural resources, `<int:param>`)
✅ SocketIO events (snake_case)
✅ JSON payloads (snake_case keys)
✅ API responses (direct format, no wrapper)
✅ Date/time format (ISO 8601 strings)
✅ Error responses (standardized structure)
✅ Error codes (ALL_CAPS_SNAKE_CASE)
✅ Exception handling (Flask error handlers + granular CV)
✅ Logging (Python logger hierarchy `deskpulse.{component}`)
✅ Log levels (ERROR/WARNING/INFO/DEBUG)
✅ Test location (separate `tests/` directory)
✅ Test naming (`test_{module}.py`, `test_{function}_{scenario}()`)
✅ Static assets (`app/static/{css,js,img}/`)
✅ Templates (`app/templates/` flat structure)
✅ File naming (snake_case modules)
✅ Class naming (PascalCase)
✅ Constant naming (UPPER_SNAKE_CASE)

**Enforcement:** Black formatter, Flake8 linter, pytest, CI/CD pipeline, code review.

**Next Steps:** Implementation begins with these patterns as the foundation for consistent, conflict-free code across all AI agents and contributors.

## Project Structure & Boundaries

### Complete Project Directory Structure

```
deskpulse/
├── README.md                          # Installation guide, quick start, FR53 documentation
├── LICENSE                            # Open source license (MIT recommended)
├── CONTRIBUTING.md                    # FR53: Development setup, contribution guidelines
├── CHANGELOG.md                       # FR60: Version history, release notes
├── .gitignore                         # Python, venv, __pycache__, .env exclusions
├── .flake8                            # Flake8 config (100-char lines, E203/W503 ignore)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # FR34: CI/CD testing pipeline
│   │   └── release.yml                # FR25: GitHub release automation
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md              # FR59: Bug reporting template
│   │   └── feature_request.md         # FR54: Good-first-issue labeling
│   └── PULL_REQUEST_TEMPLATE.md       # FR53: PR guidelines
│
├── requirements.txt                   # Production dependencies
├── requirements-dev.txt               # Development dependencies (pytest, black, flake8)
├── pyproject.toml                     # Black formatter config
├── pytest.ini                         # Pytest configuration
│
├── run.py                             # Development entry point (Flask development server)
├── wsgi.py                            # Production/systemd entry point
│
├── app/
│   ├── __init__.py                    # create_app() factory, FR1-FR60 integration
│   ├── config.py                      # Config classes (Development, Testing, Production, Systemd)
│   ├── extensions.py                  # SocketIO, database init (init_app pattern)
│   │
│   ├── core/                          # Core utilities shared across modules
│   │   ├── __init__.py
│   │   ├── exceptions.py              # Custom exception hierarchy (DeskPulseException, etc.)
│   │   └── constants.py               # Error codes, state enums, system constants
│   │
│   ├── utils/                         # Shared utility functions
│   │   ├── __init__.py
│   │   ├── time_utils.py              # ISO 8601 formatting, datetime helpers
│   │   └── response_utils.py          # Standard JSON response builders
│   │
│   ├── main/                          # Main blueprint (dashboard, health checks)
│   │   ├── __init__.py                # Blueprint registration
│   │   ├── routes.py                  # FR35-FR45: Dashboard HTTP endpoints
│   │   └── events.py                  # FR35-FR45: SocketIO event handlers (posture_update, camera_status)
│   │
│   ├── api/                           # API blueprint (future: mobile app, integrations)
│   │   ├── __init__.py                # Blueprint registration
│   │   ├── routes.py                  # FR35-FR45: RESTful API endpoints (/api/events, /api/settings)
│   │   └── schemas.py                 # API request/response validation (optional)
│   │
│   ├── cv/                            # Computer vision module (FR1-FR7)
│   │   ├── __init__.py
│   │   ├── capture.py                 # FR1: Camera capture, frame handling, VideoCapture wrapper
│   │   ├── detection.py               # FR2: MediaPipe Pose landmark detection
│   │   ├── classification.py          # FR3: Binary good/bad posture classification
│   │   └── presence.py                # FR4: User presence detection logic
│   │
│   ├── alerts/                        # Alert management module (FR8-FR13)
│   │   ├── __init__.py
│   │   ├── manager.py                 # FR8-FR10: Threshold detection, alert triggering
│   │   ├── notifier.py                # FR9: Desktop notifications (libnotify + browser)
│   │   └── state.py                   # FR11-FR13: Pause/resume controls, monitoring status
│   │
│   ├── data/                          # Data persistence module (FR14-FR23, FR46-FR52)
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite connection management (WAL mode), get_db(), close_db()
│   │   ├── models.py                  # Data models (posture_event, user_setting tables)
│   │   ├── repository.py              # FR14-FR19: CRUD operations, daily/weekly stats queries
│   │   ├── analytics.py               # FR20-FR23: Trend calculation, pattern detection, export (CSV/PDF)
│   │   └── migrations/                # FR30: Database schema migrations (future)
│   │       └── init_schema.sql        # Initial database schema creation
│   │
│   ├── system/                        # System management module (FR24-FR34)
│   │   ├── __init__.py
│   │   ├── health.py                  # FR32: System status monitoring, health checks
│   │   ├── update_checker.py          # FR25-FR26: GitHub release checking, update notifications
│   │   ├── backup.py                  # FR27-FR28: Database backup/rollback functionality
│   │   └── calibration.py             # FR34: Camera calibration utilities (future)
│   │
│   ├── static/                        # Static assets (FR35-FR45)
│   │   ├── css/
│   │   │   └── pico.min.css           # Pico CSS 7-9KB bundle
│   │   ├── js/
│   │   │   └── dashboard.js           # SocketIO client, real-time UI updates, browser notifications
│   │   └── img/
│   │       ├── logo.png
│   │       └── favicon.ico
│   │
│   └── templates/                     # Jinja2 templates (FR35-FR45)
│       ├── base.html                  # Base template with Pico CSS, semantic HTML
│       ├── dashboard.html             # FR35-FR45: Main dashboard view (live feed, charts, alerts)
│       └── settings.html              # FR31: Configuration UI (thresholds, camera device, etc.)
│
├── tests/                             # Test suite (pytest) - FR34, NFR-M2
│   ├── conftest.py                    # Test fixtures (app factory, mock camera, mock database)
│   ├── test_cv.py                     # FR1-FR7: CV pipeline unit tests (mock camera input)
│   ├── test_detection.py              # FR2: MediaPipe detection tests
│   ├── test_classification.py         # FR3: Posture classification tests
│   ├── test_alerts.py                 # FR8-FR13: Alert logic tests (threshold, notifications)
│   ├── test_database.py               # FR14-FR19: Database operations tests
│   ├── test_analytics.py              # FR20-FR23: Analytics and reporting tests
│   ├── test_routes.py                 # FR35-FR45: Flask HTTP route tests
│   ├── test_websocket.py              # FR35-FR45: SocketIO event tests
│   ├── test_api.py                    # API blueprint endpoint tests
│   ├── test_system.py                 # FR24-FR34: System management tests
│   └── test_integration.py            # End-to-end integration tests (CV → DB → SocketIO → UI)
│
├── scripts/                           # Utility scripts
│   ├── install.sh                     # FR24: One-line installer script
│   ├── setup_dev.sh                   # FR53: Development environment setup
│   ├── run_tests.sh                   # FR34: Test execution script
│   └── systemd/
│       └── deskpulse.service          # FR29: systemd service file template
│
├── config/                            # Configuration files
│   ├── config.ini.example             # System defaults (camera, alerts, dashboard)
│   └── secrets.env.example            # Secret key template (not committed to git)
│
├── data/                              # Runtime data directory (created by installer)
│   ├── deskpulse.db                   # SQLite database (FR46-FR52)
│   ├── deskpulse.db-shm               # SQLite shared memory (WAL mode)
│   ├── deskpulse.db-wal               # SQLite write-ahead log (WAL mode)
│   └── backups/                       # FR27: Database backups
│
├── logs/                              # Log files (if file-based logging used, optional)
│   └── .gitkeep                       # Keep directory in git
│
└── docs/                              # Documentation (FR53, FR57-FR60)
    ├── architecture.md                # This document! Architecture decisions
    ├── api.md                         # API documentation (endpoints, schemas)
    ├── installation.md                # Detailed installation guide
    ├── configuration.md               # Configuration options reference
    ├── troubleshooting.md             # FR57: Common issues and solutions
    ├── development.md                 # FR53: Development guide for contributors
    └── deployment.md                  # Deployment guide (systemd, Pi setup)
```

**Project Statistics:**
- **9 application modules:** main, api, cv, alerts, data, system, core, utils, extensions
- **3 static asset types:** css, js, img
- **3 Jinja2 templates:** base, dashboard, settings
- **11 test files:** Unit tests + integration tests
- **4 scripts:** Installation, dev setup, testing, systemd service
- **7 documentation files:** Architecture, API, installation, config, troubleshooting, development, deployment

---

### Architectural Boundaries

#### API Boundaries

**External HTTP API (Flask Routes):**

**Main Blueprint (`/`):**
- `GET /` - Dashboard page (serves `dashboard.html`)
- `GET /settings` - Settings page (serves `settings.html`)
- `GET /health` - Health check endpoint (FR32)

**API Blueprint (`/api/`):**
- `GET /api/events` - List posture events (pagination, date filtering)
- `GET /api/events/<int:event_id>` - Get specific event
- `GET /api/stats/daily` - Daily posture statistics (FR14-FR15)
- `GET /api/stats/weekly` - Weekly posture statistics (FR16)
- `GET /api/stats/baseline` - 7-day baseline statistics (FR17)
- `GET /api/export/csv` - Export events to CSV (FR22)
- `GET /api/export/pdf` - Export reports to PDF (FR23)
- `GET /api/settings` - Get current configuration (FR31)
- `PUT /api/settings` - Update configuration (FR31)
- `POST /api/backup` - Trigger database backup (FR27)
- `POST /api/restore` - Restore from backup (FR28)
- `GET /api/updates` - Check for updates (FR25-FR26)

**SocketIO Events (Real-Time Communication):**

**Client → Server:**
- `connect` - Client connects to dashboard
- `disconnect` - Client disconnects from dashboard
- `pause_monitoring` - User pauses posture monitoring (FR11)
- `resume_monitoring` - User resumes posture monitoring (FR12)
- `request_camera_status` - Request current camera state

**Server → Client:**
- `posture_update` - Real-time posture state change (FR35-FR38)
  ```python
  {'posture_state': 'bad', 'timestamp': '2025-12-06T14:30:00Z', 'confidence_score': 0.87}
  ```
- `camera_status` - Camera connection state (FR6)
  ```python
  {'state': 'connected|degraded|disconnected'}
  ```
- `alert_triggered` - Posture threshold alert (FR8-FR9)
  ```python
  {'message': 'Bad posture detected for 10 minutes', 'timestamp': '2025-12-06T14:30:00Z'}
  ```
- `monitoring_status` - Pause/resume status (FR13)
  ```python
  {'status': 'active|paused', 'timestamp': '2025-12-06T14:30:00Z'}
  ```

**Authentication Boundary:**
- **No authentication for MVP** - Local network only (NFR-S2)
- **Optional HTTP Basic Auth** (future) for shared network deployment

---

#### Component Boundaries

**CV Pipeline → Database:**
- **Communication:** Direct SQLite writes via `data.repository`
- **Flow:** CV thread → Queue → Database consumer writes `posture_event` records
- **Boundary:** `app/cv/` NEVER imports `app/data/`, uses dependency injection
- **Pattern:**
  ```python
  # CV thread puts data in queue
  cv_queue.put({'state': 'bad', 'timestamp': now, 'confidence': 0.87})

  # Database consumer reads from queue
  event_data = cv_queue.get()
  repository.create_posture_event(**event_data)
  ```

**CV Pipeline → SocketIO:**
- **Communication:** SocketIO emit from CV queue consumer
- **Flow:** CV thread → Queue → SocketIO emit to all clients
- **Boundary:** `app/cv/` does NOT import `app.extensions.socketio` directly
- **Pattern:**
  ```python
  # In app/main/events.py (SocketIO handler)
  from app.extensions import socketio

  @socketio.on('connect')
  def stream_posture_updates():
      while True:
          data = cv_queue.get()
          emit('posture_update', data, broadcast=True)
  ```

**Alert System → Notification:**
- **Communication:** Alert manager checks threshold → Notifier sends notifications
- **Flow:** Alert manager → Notifier (libnotify + SocketIO browser notification)
- **Boundary:** `app/alerts/manager.py` imports `app/alerts/notifier.py`
- **Pattern:**
  ```python
  # In app/alerts/manager.py
  from app.alerts.notifier import send_desktop_notification, emit_browser_notification

  if bad_posture_duration >= ALERT_THRESHOLD:
      send_desktop_notification("Bad posture: 10 minutes")
      emit_browser_notification({'message': 'Bad posture: 10 minutes'})
  ```

**Database → Analytics:**
- **Communication:** Analytics module queries via Repository
- **Flow:** Analytics → Repository → Database
- **Boundary:** `app/data/analytics.py` imports `app/data/repository.py`
- **Pattern:**
  ```python
  # In app/data/analytics.py
  from app.data.repository import get_events_by_date_range

  def calculate_weekly_stats(start_date, end_date):
      events = get_events_by_date_range(start_date, end_date)
      # Calculate statistics...
  ```

**Flask Routes → Services:**
- **Communication:** Routes call service modules, return JSON
- **Flow:** HTTP request → Route → Service → Repository → Database
- **Boundary:** Routes are thin controllers, business logic in services
- **Pattern:**
  ```python
  # In app/api/routes.py
  from app.data.analytics import calculate_daily_stats

  @api_bp.route('/api/stats/daily')
  def get_daily_stats():
      stats = calculate_daily_stats(date.today())
      return jsonify(stats)
  ```

---

#### Service Boundaries

**CV Processing Service (Dedicated Thread):**
- **Responsibility:** Camera capture, MediaPipe detection, posture classification
- **Independence:** Runs in dedicated thread, never blocks Flask/SocketIO
- **Communication:** Queue-based messaging (Python `queue.Queue`)
- **Lifecycle:** Started in `create_app()`, daemon thread (terminates with main process)

**Alert Management Service:**
- **Responsibility:** Threshold tracking, notification triggering
- **Trigger:** CV queue consumer signals alert manager on state changes
- **Communication:** Direct function calls (synchronous)
- **State:** In-memory tracking of bad posture duration

**Database Service:**
- **Responsibility:** All SQLite operations, WAL mode management
- **Access Pattern:** Repository pattern (single point of database access)
- **Lifecycle:** Connection per Flask request context (`g.db`)
- **Migrations:** Manual SQL scripts in `app/data/migrations/`

**WebSocket Service (SocketIO):**
- **Responsibility:** Real-time bidirectional communication
- **Server:** Flask-SocketIO with `async_mode='threading'`
- **Events:** posture_update, camera_status, alert_triggered, monitoring_status
- **Broadcast:** All clients receive same updates (no per-user filtering in MVP)

**System Health Service:**
- **Responsibility:** systemd watchdog pings, health checks, status reporting
- **Lifecycle:** Watchdog pings sent from CV loop every 15 seconds
- **Monitoring:** Camera status, database connectivity, disk space

---

#### Data Boundaries

**Database Schema:**

**Primary Table: `posture_event`**
```sql
CREATE TABLE posture_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    posture_state TEXT NOT NULL,      -- 'good' or 'bad'
    user_present BOOLEAN DEFAULT 1,
    confidence_score REAL,             -- MediaPipe confidence (0.0-1.0)
    metadata JSON                      -- Extensible: pain_level, phone_detected, focus_metrics
);
CREATE INDEX idx_posture_event_timestamp ON posture_event(timestamp);
CREATE INDEX idx_posture_event_state ON posture_event(posture_state);
```

**Secondary Table: `user_setting`**
```sql
CREATE TABLE user_setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,          -- Setting name (e.g., 'alert_threshold')
    value TEXT NOT NULL,               -- Setting value (JSON-serialized if complex)
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Data Access Patterns:**

**Write Pattern (CV Pipeline):**
```python
# High-frequency writes (5-15 FPS)
# Batched or async to avoid blocking CV thread
def record_posture_event(state, confidence, metadata=None):
    db = get_db()
    db.execute(
        "INSERT INTO posture_event (timestamp, posture_state, confidence_score, metadata) "
        "VALUES (?, ?, ?, ?)",
        (datetime.now(), state, confidence, json.dumps(metadata) if metadata else None)
    )
    db.commit()
```

**Read Pattern (Analytics):**
```python
# Time-range queries for statistics
def get_daily_events(date):
    db = get_db()
    cursor = db.execute(
        "SELECT * FROM posture_event "
        "WHERE date(timestamp) = ? "
        "ORDER BY timestamp DESC",
        (date,)
    )
    return cursor.fetchall()
```

**Data Retention:**
- **Free Tier:** 7-day rolling window (auto-delete events older than 7 days)
- **Pro Tier:** 30+ day retention (configurable)
- **Cleanup:** Daily cron job or background task deletes old events

**Caching Strategy:**
- **No caching in MVP** - SQLite fast enough for single-device deployment
- **Future:** Redis for multi-user Pro tier (optional)

---

### Requirements to Structure Mapping

#### FR1-FR7: Posture Monitoring → `app/cv/`

**FR1: Continuous video capture**
- `app/cv/capture.py` - `CameraCapture` class wraps `cv2.VideoCapture`
- Dedicated thread in CV pipeline loop
- Tests: `tests/test_cv.py::test_camera_capture_continuous()`

**FR2: MediaPipe Pose detection**
- `app/cv/detection.py` - `PoseDetector` class wraps MediaPipe Pose
- Processes frames from capture, returns landmarks
- Tests: `tests/test_detection.py::test_mediapipe_pose_detection()`

**FR3: Posture classification**
- `app/cv/classification.py` - `PostureClassifier` class
- Binary good/bad logic based on landmark confidence
- Tests: `tests/test_classification.py::test_classify_posture_good_state()`

**FR4: User presence detection**
- `app/cv/presence.py` - `PresenceDetector` class
- Detects no landmarks = user absent
- Tests: `tests/test_cv.py::test_user_presence_detection()`

**FR5: Camera disconnect detection**
- `app/cv/capture.py` - Camera state machine (connected/degraded/disconnected)
- Graceful degradation with 3-retry logic
- Tests: `tests/test_cv.py::test_camera_disconnect_handling()`

**FR6: Camera reconnection**
- `app/cv/capture.py` - Retry loop with 10-second backoff
- SocketIO emit `camera_status` event
- Tests: `tests/test_cv.py::test_camera_reconnect_success()`

**FR7: Continuous 8+ hour operation**
- CV pipeline loop with memory profiling
- systemd watchdog integration
- Tests: `tests/test_integration.py::test_long_running_operation()` (stress test)

---

#### FR8-FR13: Alert & Notification → `app/alerts/`

**FR8-FR10: Threshold detection & alerts**
- `app/alerts/manager.py` - `AlertManager` class tracks bad posture duration
- Configurable threshold (default 10 minutes)
- Tests: `tests/test_alerts.py::test_alert_threshold_triggered()`

**FR9: Desktop notifications**
- `app/alerts/notifier.py` - Hybrid libnotify + browser notifications
- `send_desktop_notification()` - subprocess call to `notify-send`
- `emit_browser_notification()` - SocketIO emit `alert_triggered`
- Tests: `tests/test_alerts.py::test_desktop_notification_sent()`

**FR11-FR13: Pause/resume controls**
- `app/alerts/state.py` - `MonitoringState` class (active/paused)
- SocketIO events `pause_monitoring`, `resume_monitoring`
- Tests: `tests/test_alerts.py::test_pause_resume_monitoring()`

---

#### FR14-FR23: Analytics & Reporting → `app/data/`

**FR14-FR19: Statistics & baseline**
- `app/data/analytics.py` - `calculate_daily_stats()`, `calculate_weekly_stats()`, `calculate_baseline()`
- `app/data/repository.py` - Database query helpers
- Tests: `tests/test_analytics.py::test_daily_stats_calculation()`

**FR20: Pain tracking (optional)**
- `app/data/models.py` - `metadata` JSON field in `posture_event` table
- Store `{"pain_level": 3}` in metadata
- Tests: `tests/test_database.py::test_store_pain_level_metadata()`

**FR21: Pattern detection**
- `app/data/analytics.py` - `detect_patterns()` function
- Analyzes time-series data for trends
- Tests: `tests/test_analytics.py::test_pattern_detection()`

**FR22-FR23: CSV/PDF export**
- `app/data/analytics.py` - `export_to_csv()`, `export_to_pdf()`
- Flask route `/api/export/csv`, `/api/export/pdf`
- Tests: `tests/test_analytics.py::test_csv_export()`

---

#### FR24-FR34: System Management → `app/system/` + `scripts/`

**FR24: One-line installer**
- `scripts/install.sh` - Bash script for automated setup
- Installs dependencies, creates venv, configures systemd
- Tests: Manual testing on fresh Pi OS installation

**FR25-FR26: Update checking**
- `app/system/update_checker.py` - Queries GitHub API for latest release
- Flask route `/api/updates`
- Tests: `tests/test_system.py::test_update_check()`

**FR27-FR28: Database backup/rollback**
- `app/system/backup.py` - SQLite backup to `data/backups/`
- Flask routes `/api/backup`, `/api/restore`
- Tests: `tests/test_system.py::test_database_backup_restore()`

**FR29: systemd auto-start**
- `scripts/systemd/deskpulse.service` - systemd service file
- Installed by `scripts/install.sh`
- Tests: Manual systemd testing

**FR30: Database migrations**
- `app/data/migrations/init_schema.sql` - Initial schema
- Future: Alembic or custom migration tool
- Tests: `tests/test_database.py::test_schema_migration()`

**FR31: Configuration management**
- `config/config.ini.example` - INI config file
- `app/config.py` - ConfigParser integration
- Flask route `/api/settings` (GET/PUT)
- Tests: `tests/test_system.py::test_configuration_update()`

**FR32: System status monitoring**
- `app/system/health.py` - Health check logic
- Flask route `/health`
- Tests: `tests/test_system.py::test_health_check_endpoint()`

**FR33: Operational event logging**
- Python logger hierarchy (`deskpulse.{component}`)
- systemd journal integration
- Tests: `tests/test_integration.py::test_logging_output()`

**FR34: Camera calibration**
- `app/system/calibration.py` - Camera calibration utilities (future)
- Tests: Deferred to Month 2-3

---

#### FR35-FR45: Dashboard & Visualization → `app/main/` + `app/templates/` + `app/static/`

**FR35-FR38: Web dashboard with live feed**
- `app/templates/dashboard.html` - Main dashboard UI
- `app/static/js/dashboard.js` - SocketIO client, real-time updates
- `app/main/routes.py` - Route `GET /`
- Tests: `tests/test_routes.py::test_dashboard_page_loads()`

**FR39-FR40: Real-time WebSocket updates**
- `app/main/events.py` - SocketIO event handlers
- `app/extensions.py` - SocketIO initialization
- Tests: `tests/test_websocket.py::test_posture_update_event()`

**FR41: Multi-device simultaneous viewing**
- SocketIO broadcast to all connected clients
- Tests: `tests/test_websocket.py::test_multiple_clients_connected()`

**FR42-FR45: Charts, graphs, customization**
- `app/templates/dashboard.html` - Chart.js integration (future)
- `app/static/js/dashboard.js` - Chart rendering
- Tests: `tests/test_routes.py::test_dashboard_charts_rendered()`

---

#### FR46-FR52: Data Management → `app/data/`

**FR46-FR48: SQLite local storage**
- `app/data/database.py` - SQLite connection, WAL mode
- `app/data/models.py` - Schema definitions
- Tests: `tests/test_database.py::test_sqlite_wal_mode_enabled()`

**FR49-FR50: 7-day vs 30+ day retention**
- `app/data/repository.py` - Data cleanup logic
- Free tier: Auto-delete events > 7 days
- Pro tier: Configurable retention
- Tests: `tests/test_database.py::test_data_retention_cleanup()`

**FR51: Optional encryption**
- Future: SQLCipher integration (Pro tier)
- Tests: Deferred to Pro tier implementation

**FR52: User data deletion**
- Flask route `/api/data/delete` (future)
- Tests: Deferred to Month 2-3

---

#### FR53-FR60: Community & Contribution → `docs/` + `.github/`

**FR53: CONTRIBUTING.md**
- `CONTRIBUTING.md` - Development setup, PR guidelines
- `docs/development.md` - Detailed contributor guide

**FR54: Good-first-issue labeling**
- `.github/ISSUE_TEMPLATE/feature_request.md`
- GitHub issue labels managed manually

**FR55: Development environment setup**
- `scripts/setup_dev.sh` - Automated dev setup
- `README.md` - Quick start guide

**FR56-FR57: Comprehensive documentation**
- `docs/installation.md` - Installation guide
- `docs/troubleshooting.md` - Common issues
- `docs/api.md` - API reference
- `docs/configuration.md` - Config options

**FR58: GitHub issue tracking**
- `.github/ISSUE_TEMPLATE/bug_report.md`

**FR59: Automated testing (CI/CD)**
- `.github/workflows/ci.yml` - GitHub Actions pipeline
- `scripts/run_tests.sh` - Test runner script

**FR60: Changelog maintenance**
- `CHANGELOG.md` - Version history

---

### Integration Points

#### Internal Communication

**CV Thread → Database Consumer:**
```python
# CV thread produces events
cv_queue = queue.Queue(maxsize=1)  # Latest state only

def cv_pipeline_loop():
    while True:
        # ... capture, detect, classify ...
        cv_queue.put({
            'posture_state': state,
            'timestamp': datetime.now(),
            'confidence_score': confidence,
            'user_present': user_present
        })

# Database consumer thread
def database_consumer():
    while True:
        event_data = cv_queue.get()
        repository.create_posture_event(**event_data)
        check_alert_threshold(event_data)  # Alert manager
```

**Database → SocketIO:**
```python
# After database write, emit to all clients
def database_consumer():
    while True:
        event_data = cv_queue.get()
        repository.create_posture_event(**event_data)

        # Emit to SocketIO clients
        socketio.emit('posture_update', {
            'posture_state': event_data['posture_state'],
            'timestamp': event_data['timestamp'].isoformat(),
            'confidence_score': event_data['confidence_score']
        }, broadcast=True)
```

**Alert Manager → Notifier:**
```python
def check_alert_threshold(event_data):
    if event_data['posture_state'] == 'bad':
        bad_posture_duration += time_delta

        if bad_posture_duration >= ALERT_THRESHOLD:
            # Desktop notification
            send_desktop_notification("Bad posture: 10 minutes")

            # Browser notification via SocketIO
            socketio.emit('alert_triggered', {
                'message': 'Bad posture detected for 10 minutes',
                'timestamp': datetime.now().isoformat()
            }, broadcast=True)
```

---

#### External Integrations

**GitHub API (Update Checking):**
- **Endpoint:** `https://api.github.com/repos/{owner}/deskpulse/releases/latest`
- **Method:** GET (unauthenticated, public repo)
- **Frequency:** Manual check via `/api/updates` or daily background task
- **Response:** Parse `tag_name` for version comparison

**MediaPipe Pose (Google):**
- **Library:** `mediapipe` Python package
- **Model:** Pre-trained Pose Landmarker (~2GB)
- **License:** Apache 2.0
- **Integration:** `app/cv/detection.py` imports `mediapipe.solutions.pose`

**OpenCV (Camera Interface):**
- **Library:** `opencv-python` package
- **Integration:** `app/cv/capture.py` imports `cv2.VideoCapture`
- **Platform:** Linux (Raspberry Pi OS)

**libnotify (Desktop Notifications):**
- **System:** `libnotify-bin` package (pre-installed on Pi OS Desktop)
- **Integration:** `subprocess.run(['notify-send', 'DeskPulse', message])`

**systemd (Service Management):**
- **Integration:** `sdnotify` Python package for watchdog pings
- **Service:** `scripts/systemd/deskpulse.service`

---

#### Data Flow

**Real-Time Posture Monitoring Flow:**
```
1. Camera capture (app/cv/capture.py)
   └→ cv2.VideoCapture.read() → frame

2. MediaPipe detection (app/cv/detection.py)
   └→ pose.process(frame) → landmarks

3. Posture classification (app/cv/classification.py)
   └→ classify_posture(landmarks) → 'good' or 'bad'

4. Queue event (CV thread)
   └→ cv_queue.put({'state': 'bad', 'timestamp': now, 'confidence': 0.87})

5. Database write (Database consumer thread)
   └→ repository.create_posture_event() → INSERT INTO posture_event

6. Alert check (Alert manager)
   └→ IF bad_posture >= 10 min → send_desktop_notification()

7. SocketIO broadcast (Database consumer)
   └→ socketio.emit('posture_update', data) → All connected browsers

8. Browser update (JavaScript)
   └→ Update dashboard UI, show notification
```

**Statistics Query Flow:**
```
1. User requests daily stats (Browser)
   └→ Fetch /api/stats/daily

2. Flask route handler (app/api/routes.py)
   └→ calculate_daily_stats(date.today())

3. Analytics module (app/data/analytics.py)
   └→ repository.get_events_by_date_range(start, end)

4. Repository query (app/data/repository.py)
   └→ SELECT * FROM posture_event WHERE date(timestamp) = ?

5. Database (SQLite)
   └→ Returns rows (id, timestamp, posture_state, confidence_score, metadata)

6. Analytics calculation
   └→ Calculate good%, bad%, average confidence, trends

7. JSON response
   └→ return jsonify({'good_percentage': 75.2, 'bad_percentage': 24.8, ...})

8. Browser renders (JavaScript)
   └→ Update chart, display statistics
```

---

### File Organization Patterns

#### Configuration Files

**Root-Level Configuration:**
- `.flake8` - Flake8 linter configuration (100-char lines, E203/W503 ignore)
- `pyproject.toml` - Black formatter configuration
- `pytest.ini` - Pytest configuration (test discovery, coverage)
- `.gitignore` - Python-specific exclusions (venv, __pycache__, .env, *.db)

**Application Configuration:**
- `config/config.ini.example` - System defaults, user-editable
- `~/.config/deskpulse/config.ini` - User overrides (created by installer)
- `config/secrets.env.example` - Secret key template (not committed)

**Development Configuration:**
- `.github/workflows/ci.yml` - CI/CD pipeline (Black, Flake8, pytest)
- `scripts/systemd/deskpulse.service` - systemd service template

---

#### Source Organization

**Application Factory Pattern:**
```
app/
├── __init__.py          # create_app() factory
├── config.py            # Config classes
├── extensions.py        # SocketIO, database init
│
├── core/                # Shared core utilities
├── utils/               # Shared helper functions
├── main/                # Main blueprint (dashboard)
├── api/                 # API blueprint (REST endpoints)
├── cv/                  # Computer vision module
├── alerts/              # Alert management
├── data/                # Data persistence
├── system/              # System management
│
├── static/              # Static assets
└── templates/           # Jinja2 templates
```

**Module Organization Pattern:**
Each feature module follows:
```
module_name/
├── __init__.py          # Module exports
├── service.py           # Business logic
├── models.py            # Data models (optional)
└── utils.py             # Module-specific helpers (optional)
```

---

#### Test Organization

**Pytest Structure:**
```
tests/
├── conftest.py          # Global fixtures (app factory, mock camera, mock DB)
├── test_{module}.py     # Unit tests per module
└── test_integration.py  # End-to-end integration tests
```

**Test File Naming:**
- `test_{module}.py` - Matches `app/{module}/` structure
- `test_routes.py` - Tests `app/main/routes.py` + `app/api/routes.py`
- `test_websocket.py` - Tests `app/main/events.py` SocketIO handlers

**Test Function Naming:**
- `test_{function}_{scenario}()` - Descriptive function + scenario
- Example: `test_classify_posture_good_state()`, `test_camera_reconnect_on_failure()`

---

#### Asset Organization

**Static Assets:**
```
app/static/
├── css/
│   └── pico.min.css     # 7-9KB bundle, served directly (no build step)
├── js/
│   └── dashboard.js     # SocketIO client, Chart.js integration
└── img/
    ├── logo.png
    └── favicon.ico
```

**Templates:**
```
app/templates/
├── base.html            # Base layout, Pico CSS, semantic HTML
├── dashboard.html       # Extends base, main dashboard view
└── settings.html        # Extends base, configuration UI
```

**Runtime Data:**
```
data/
├── deskpulse.db         # SQLite database (created on first run)
├── deskpulse.db-shm     # Shared memory (WAL mode)
├── deskpulse.db-wal     # Write-ahead log (WAL mode)
└── backups/
    └── deskpulse_{timestamp}.db  # Timestamped backups
```

---

### Development Workflow Integration

#### Development Server Structure

**Run Development Server:**
```bash
# Activate venv
source venv/bin/activate

# Run development server
python run.py
# OR
flask --app app run --debug
```

**Development Entry Point (`run.py`):**
```python
from app import create_app

app = create_app('development')

if __name__ == '__main__':
    # SECURITY NFR-S2: Use HOST from config (defaults to 127.0.0.1)
    # For local network access, set FLASK_HOST environment variable
    from app.extensions import socketio
    socketio.run(
        app,
        host=app.config.get('HOST', '127.0.0.1'),
        port=app.config.get('PORT', 5000),
        debug=True
    )
```

**Hot Reloading:**
- Flask development server auto-reloads on file changes
- CV thread restarts with new code
- Database connections reset

---

#### Build Process Structure

**No Build Step Required:**
- Flask serves static files directly
- Pico CSS pre-minified (7-9KB)
- JavaScript vanilla (no transpilation needed)

**Optional Build Tasks (Future):**
- CSS minification (if custom CSS added)
- JavaScript bundling (if multiple JS files)
- Asset versioning for cache busting

---

#### Deployment Structure

**Production Deployment (systemd):**

**Entry Point (`wsgi.py`):**
```python
from app import create_app

app = create_app('production')
```

**systemd Service (`/etc/systemd/system/deskpulse.service`):**
```ini
[Unit]
Description=DeskPulse Posture Monitoring Service
After=network.target

[Service]
Type=notify
User=pi
WorkingDirectory=/home/pi/deskpulse
Environment="PATH=/home/pi/deskpulse/venv/bin"
Environment="DESKPULSE_SECRET_KEY=generated-at-install"
EnvironmentFile=-/etc/deskpulse/secrets.env
ExecStart=/home/pi/deskpulse/venv/bin/python wsgi.py
WatchdogSec=30
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Deployment Steps:**
1. `scripts/install.sh` - Automated installation
2. `systemctl enable deskpulse` - Enable auto-start
3. `systemctl start deskpulse` - Start service
4. `journalctl -u deskpulse -f` - Monitor logs

---

### Architecture Summary

**Complete DeskPulse structure defined:**

✅ **60 functional requirements** mapped to specific files and directories
✅ **9 application modules** with clear responsibilities and boundaries
✅ **11 test files** covering unit + integration testing (NFR-M2: 70%+ coverage)
✅ **7 documentation files** supporting FR53-FR60 (community & contribution)
✅ **Flask Application Factory pattern** with blueprints, extensions, config classes
✅ **Architectural boundaries** defined for API, components, services, data
✅ **Integration points** documented for internal and external communication
✅ **Data flow** mapped from camera → CV → database → SocketIO → browser
✅ **Deployment structure** optimized for Raspberry Pi systemd service

**Next Step:** Architecture document is now complete and ready for implementation. AI agents can use this as the definitive guide for building DeskPulse with consistent, conflict-free code.
