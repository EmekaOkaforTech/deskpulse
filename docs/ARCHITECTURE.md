# DeskPulse Architecture

Technical reference for contributors. Covers system design, component responsibilities,
technology decisions, and data flow.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Directory Structure](#directory-structure)
3. [Component Architecture](#component-architecture)
4. [Threading Model](#threading-model)
5. [Data Flow](#data-flow)
6. [Database Design](#database-design)
7. [Configuration System](#configuration-system)
8. [Security Design](#security-design)
9. [Technology Decisions](#technology-decisions)
10. [Deployment Architecture](#deployment-architecture)

---

## System Overview

DeskPulse is a locally-hosted web application that runs on Raspberry Pi. It captures
webcam frames, detects body pose landmarks using MediaPipe, classifies posture as good
or bad, and serves a real-time dashboard over the local network.

**Key design constraint:** All processing is on-device. No frames, posture data, or
analytics leave the machine at any point.

```
USB Webcam → CV Pipeline (thread) → Posture Classification → SocketIO → Browser Dashboard
                                  ↓
                             SQLite (local)
                                  ↓
                          Analytics Engine → API → Dashboard
```

---

## Directory Structure

```
deskpulse/
├── app/                        # Application package
│   ├── __init__.py             # App factory (create_app)
│   ├── config.py               # Configuration classes
│   ├── extensions.py           # Flask extension initialisation
│   ├── __version__.py          # Single version source of truth
│   ├── alerts/                 # Alert threshold tracking & notifications
│   │   ├── manager.py          # AlertManager: threshold state machine
│   │   └── notifier.py         # Desktop (libnotify) + browser notifications
│   ├── api/                    # REST API blueprint
│   │   └── routes.py           # /api/stats, /api/trend, /api/version, etc.
│   ├── core/                   # Cross-cutting infrastructure
│   │   ├── constants.py        # Application-wide constants
│   │   ├── exceptions.py       # Custom exception hierarchy
│   │   └── logging.py          # Logging config (systemd journal + console)
│   ├── cv/                     # Computer vision subsystem
│   │   ├── capture.py          # CameraCapture: OpenCV VideoCapture wrapper
│   │   ├── detection.py        # PoseDetector: MediaPipe Tasks API wrapper
│   │   ├── classification.py   # PostureClassifier: angle-based binary classification
│   │   ├── pipeline.py         # CVPipeline: orchestrates CV thread
│   │   ├── pose_landmarks.py   # MediaPipe landmark index constants
│   │   ├── camera_error_handler_linux.py  # Linux-specific camera error handling
│   │   ├── camera_permissions_linux.py    # Video group / device permission checks
│   │   └── models/             # MediaPipe .task model files (not in git)
│   ├── data/                   # Data layer
│   │   ├── database.py         # SQLite connection management, WAL mode
│   │   ├── repository.py       # PostureEventRepository, AchievementRepository
│   │   ├── analytics.py        # PostureAnalytics: stats, trends, format helpers
│   │   ├── achievements.py     # AchievementService: business logic for awards
│   │   └── migrations/
│   │       └── init_schema.sql # Schema definition (idempotent, IF NOT EXISTS)
│   ├── main/                   # Main web blueprint
│   │   ├── routes.py           # Dashboard HTML route (/)
│   │   └── events.py           # SocketIO event handlers
│   ├── system/                 # System integration
│   │   ├── scheduler.py        # DailyScheduler: background task runner
│   │   └── watchdog.py         # systemd watchdog ping manager
│   ├── utils/                  # Shared utilities
│   │   ├── response_utils.py   # Consistent JSON response helpers
│   │   └── time_utils.py       # Timezone-safe datetime helpers
│   ├── static/                 # CSS, JS, images
│   └── templates/              # Jinja2 HTML templates
├── docs/                       # Documentation
├── scripts/                    # Installation and service scripts
│   ├── install.sh              # One-line installer (main entry point)
│   ├── install_service.sh      # systemd service setup
│   ├── setup_config.sh         # Configuration file setup
│   ├── systemd/                # Service unit file
│   └── templates/              # Config and secrets file templates
├── tests/                      # Test suite (pytest)
├── data/                       # Runtime data directory (created at install)
├── run.py                      # Development server entry point
├── wsgi.py                     # Production WSGI entry point (gunicorn)
└── start.sh                    # Convenience start script
```

---

## Component Architecture

DeskPulse uses the **Flask Application Factory** pattern. All components are
initialised inside `create_app()`, which accepts a config name string. This
enables clean separation between development, testing, and production configs
and makes the test suite fully self-contained.

### App Factory (`app/__init__.py`)

```python
def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(f"app.config.{config_name.capitalize()}Config")
    configure_logging(app)
    init_db(app)           # Database schema
    init_extensions(app)   # SocketIO, Talisman (CSP)
    register_blueprints(app)
    start_cv_pipeline(app) # CV thread
    start_scheduler(app)   # Background tasks
    return app
```

### Blueprints

| Blueprint | Prefix | Responsibility |
|-----------|--------|---------------|
| `main` | `/` | Dashboard HTML, SocketIO events |
| `api` | `/api` | REST endpoints for stats, trends, version |

### CV Subsystem (`app/cv/`)

Three classes with single responsibilities, composed by `CVPipeline`:

| Class | Responsibility |
|-------|---------------|
| `CameraCapture` | OpenCV VideoCapture wrapper; frame acquisition; resolution config |
| `PoseDetector` | MediaPipe Tasks API wrapper; returns 33 pose landmarks per frame |
| `PostureClassifier` | Angle-based classification; good vs bad based on shoulder-hip-nose geometry |

### Alert System (`app/alerts/`)

`AlertManager` is a state machine with four states:

```
MONITORING_ACTIVE → bad posture detected → TRACKING_BAD_POSTURE
TRACKING_BAD_POSTURE → threshold exceeded → ALERT_TRIGGERED
ALERT_TRIGGERED → cooldown elapsed → MONITORING_ACTIVE
MONITORING_ACTIVE ↔ PAUSED (user-controlled via pause/resume API)
```

Threshold and cooldown are configurable via `config.ini`:

```ini
[alerts]
posture_threshold_minutes = 10   ; Minutes of bad posture before alert
notification_enabled = true
```

`AlertNotifier` delivers notifications through two channels in parallel:
- **Desktop:** `libnotify` via `subprocess` (Linux/Raspberry Pi OS)
- **Browser:** SocketIO `alert` event (all connected clients)

### Analytics Engine (`app/data/analytics.py`)

`PostureAnalytics` performs all calculations from raw `posture_event` rows:

- `calculate_daily_stats(date)` — good/bad duration, posture score, event count
- `get_7_day_history()` — calls daily stats for each of the last 7 days
- `calculate_trend(history)` — linear regression direction over the 7-day window
- `format_duration(seconds)` — human-readable time strings (`"2h 15m"`, `"45s"`)

The engine reads directly from SQLite on each call. There is no caching layer;
response times on Raspberry Pi are under 50ms for 7-day windows.

### Achievement System (`app/data/achievements.py`)

`AchievementService` checks achievement criteria after each daily stats calculation.
Achievements are stored in `achievement_type` (definitions) and `achievement_earned`
(award records). All checks are idempotent — re-running never creates duplicates.

Nine achievements ship with the open-source edition across three categories:
daily performance, weekly consistency, and one-time milestones.

### Scheduler (`app/system/scheduler.py`)

`DailyScheduler` runs in a daemon thread and executes daily tasks using the
`schedule` library. Currently manages the end-of-day summary report (sent at
23:55 each day). All scheduled tasks run inside `app.app_context()`.

### systemd Integration (`app/system/watchdog.py`)

`WatchdogManager` sends `WATCHDOG=1` pings to systemd at a configurable interval
(default 30 seconds). If pings stop, systemd restarts the service. The module
gracefully degrades: if `sdnotify` is not installed or `NOTIFY_SOCKET` is not
set, pings are silently skipped.

---

## Threading Model

DeskPulse runs three concurrent threads in production:

```
Main Thread (Flask/Gunicorn)
├── Handles HTTP requests and SocketIO connections
├── Reads from cv_queue (non-blocking, latest-wins)
└── Responds to pause/resume API calls

CV Thread (daemon=False, name="CVPipeline-*")
├── Camera frame capture (OpenCV)
├── Pose detection (MediaPipe, ~150-200ms/frame)
├── Posture classification (angle calculation, <1ms)
├── Puts result into cv_queue (maxsize=1, drops stale frames)
├── Emits SocketIO events (posture_update, camera_status)
└── Pings systemd watchdog every 30s

Scheduler Thread (daemon=True)
└── Runs scheduled tasks (end-of-day summary at 23:55)
```

**Thread safety notes:**

- `cv_queue` uses `maxsize=1` (latest-wins semantic). If the main thread is
  slow, old CV results are discarded automatically via `queue.put_nowait()`.
- `AlertManager` state (`monitoring_paused`, `bad_posture_start_time`) is
  accessed from both the CV thread and Flask routes. Safety relies on CPython's
  GIL for atomic bool/float operations. This is intentional and documented —
  DeskPulse targets CPython on Raspberry Pi OS only.
- `CVPipeline.thread` is `daemon=False` because OpenCV's VideoCapture requires
  the thread to complete its release sequence on shutdown. A daemon thread would
  be killed mid-release, leaving the camera device locked.

---

## Data Flow

### Real-time posture update (10 FPS path)

```
1. CameraCapture.read_frame()        → BGR numpy array
2. PoseDetector.detect(frame)        → List[PoseLandmark] (33 points)
3. PostureClassifier.classify(lm)    → {'state': 'good'|'bad', 'confidence': float}
4. AlertManager.process_posture_update() → alert decision
5. PostureEventRepository.insert_posture_event() → SQLite write
6. JPEG encode frame (quality 80)    → base64 string
7. socketio.emit('posture_update', {...}) → all connected browsers
```

### Analytics request path

```
Browser GET /api/stats
  → Flask route handler
  → PostureAnalytics.calculate_daily_stats(today)
  → PostureEventRepository.get_events_for_date(today)
  → SQLite SELECT (WAL read, non-blocking)
  → JSON response
```

### Alert delivery path

```
AlertManager detects threshold exceeded
  → AlertNotifier.send_alert()
      ├── subprocess: notify-send "DeskPulse" (desktop notification)
      └── socketio.emit('alert', {...}) (browser notification)
```

---

## Database Design

SQLite with **WAL (Write-Ahead Logging)** mode enabled on every connection.

WAL is chosen over the default journal mode because:
- Readers do not block writers; writers do not block readers
- Critical for concurrent Flask requests + CV thread writes at 10 FPS
- Crash-safe: partial writes are rolled back from the WAL on next open

**Schema summary:**

```sql
posture_event          -- Core: one row per CV frame (10/sec, pruned over time)
  id, timestamp, posture_state ('good'|'bad'), user_present, confidence_score, metadata (JSON)

user_setting           -- Key-value store for user preferences
  id, key, value, updated_at

achievement_type       -- Achievement definitions (seeded at init, rarely changes)
  id, code, name, description, category, icon, points, tier, is_active

achievement_earned     -- One row per unlocked achievement
  id, achievement_type_id, earned_at, metadata (JSON), notified

achievement_progress   -- Daily tracking to prevent duplicate daily awards
  id, achievement_code, tracking_date, progress_value, target_value, completed
```

**Indexes:** `posture_event.timestamp`, `posture_event.posture_state`,
`achievement_type.code`, `achievement_earned.earned_at` — all queries
filter by date range or code lookup, so these four indexes cover all hot paths.

**Schema initialisation** is idempotent (`IF NOT EXISTS` throughout). The
same SQL runs at both app startup (file databases) and per-connection (in-memory
test databases). This dual-init pattern is documented in `app/data/database.py`.

**Database location:**

| Environment | Path |
|-------------|------|
| Production (systemd) | `/var/lib/deskpulse/deskpulse.db` |
| Development | `./data/deskpulse.db` |
| Tests | `:memory:` (per-test isolation) |

---

## Configuration System

Configuration is layered (highest priority wins):

```
1. Environment variables          → secrets only (DESKPULSE_SECRET_KEY)
2. User config (~/.config/deskpulse/config.ini)
3. System config (/etc/deskpulse/config.ini)
4. Hardcoded defaults in Config class
```

`config.py` uses `configparser` to merge layers 2–4 at import time.
Flask config objects (`DevelopmentConfig`, `ProductionConfig`, `TestingConfig`)
inherit from the base `Config` class and override as needed.

`TestingConfig` hardcodes all values — it does **not** read INI files — ensuring
test runs are deterministic regardless of the developer's local config.

**Key configuration sections:**

```ini
[camera]
device = 0                    ; /dev/video0
resolution = 720p             ; 480p | 720p | 1080p
fps_target = 10

[alerts]
posture_threshold_minutes = 10
notification_enabled = true

[dashboard]
host = 127.0.0.1              ; Bind to localhost (secure default)
port = 5000
update_interval_seconds = 2
```

**Secrets** (`DESKPULSE_SECRET_KEY`) are never read from INI files. The installer
generates a 32-byte random secret via `openssl rand -hex 32` and writes it to
`/etc/deskpulse/secrets.env` with permissions `600`.

---

## Security Design

| Control | Implementation |
|---------|---------------|
| **Localhost-only binding** | Default `HOST=127.0.0.1`; network access requires explicit user opt-in via config |
| **Content Security Policy** | Flask-Talisman enforces CSP headers — blocks XSS, clickjacking, code injection |
| **Secret key** | 32-byte random value generated at install time; never committed or logged |
| **Input validation** | All API inputs validated and type-checked before database operations |
| **No cloud egress** | Zero outbound connections; no telemetry, no analytics, no update checks |
| **SQL injection** | All queries use parameterised statements via `sqlite3` placeholder API |
| **Camera data** | Frames processed in-memory and discarded; JPEG thumbnails sent over LAN only |
| **File permissions** | `/etc/deskpulse/secrets.env` set to `600` (owner-read only) at install |

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Web framework | Flask 3.0 | Lightweight, well-understood, excellent Raspberry Pi compatibility |
| Real-time updates | Flask-SocketIO | WebSocket with fallback to long-polling; works on all browsers on LAN |
| Pose detection | MediaPipe Tasks API 0.10.x | Best accuracy/performance tradeoff on ARM64; `.task` model files are self-contained |
| Computer vision | OpenCV | Industry standard; VideoCapture supports V4L2 on Linux |
| Database | SQLite + WAL | Zero-config, file-based, concurrent-read safe, sufficient for single-device workload |
| CSS framework | Pico CSS | Semantic HTML with minimal class overhead; fast load on local network |
| Service management | systemd | Native to Raspberry Pi OS; provides auto-restart, logging, boot integration |
| Python constraint | 3.9–3.11 | MediaPipe ARM64 wheels are not available for Python 3.12+ |
| Security headers | Flask-Talisman | Production-ready CSP with minimal configuration |

---

## Deployment Architecture

### Production (Raspberry Pi)

```
systemd (boot)
  └── gunicorn (wsgi.py) ← /etc/deskpulse/secrets.env
        └── Flask app
              ├── CV Thread (OpenCV + MediaPipe)
              ├── Scheduler Thread (daily tasks)
              └── SocketIO (gevent or eventlet)

Local Network
  Browser → http://raspberrypi.local:5000
```

### Development

```
python run.py → Flask dev server (single process, auto-reload)
```

### Testing

```
pytest → TestingConfig (in-memory SQLite, mocked camera, no CV thread)
```

The CV pipeline is **not started** in test mode (`MOCK_CAMERA=True` in
`TestingConfig`). Tests that need CV behaviour mock `CameraCapture`,
`PoseDetector`, and `PostureClassifier` individually.
