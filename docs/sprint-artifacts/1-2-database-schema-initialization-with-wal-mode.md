# Story 1.2: Database Schema Initialization with WAL Mode

**Epic:** 1 - Foundation Setup & Installation
**Story ID:** 1.2
**Story Key:** 1-2-database-schema-initialization-with-wal-mode
**Status:** Done
**Priority:** Critical (Required for all data persistence features)

---

## User Story

**As a** system administrator installing DeskPulse,
**I want** the SQLite database to be created automatically with crash-resistant WAL mode,
**So that** posture data is protected from corruption during power failures or ungraceful shutdowns.

---

## Business Context & Value

**Epic Goal:** Users can install DeskPulse on their Raspberry Pi and verify the system is running correctly. This epic establishes the technical foundation that enables all subsequent user-facing features.

**User Value:** Technical users can install DeskPulse knowing their data is protected from corruption, even during power failures or ungraceful shutdowns common with Raspberry Pi devices.

**Story-Specific Value:**
- Prevents data corruption during power failures (common on Raspberry Pi)
- Enables crash-resistant data persistence without ORM overhead
- Provides flexible schema for future feature additions without painful migrations
- Establishes data foundation for all analytics and reporting features

**PRD Coverage (Epic 1):**
- FR46: Local SQLite storage with timestamps and binary classifications
- FR47: SQLite WAL mode for crash resistance (NFR-R3)
- FR14-FR23: Analytics & Reporting (requires data persistence layer)
- NFR-R3: SQLite integrity during ungraceful shutdowns

**Dependencies on Epic Goals:**
- Supports Epic 2 (Real-Time Posture Monitoring) - requires posture_event table
- Supports Epic 4 (Progress Tracking & Analytics) - requires historical data storage
- Enables Week 2 features (pain tracking via JSON metadata)

---

## Acceptance Criteria

### AC1: Database File Creation

**Given** the Flask application is starting for the first time
**When** the database initialization runs
**Then** the SQLite database is created at `data/deskpulse.db`
**And** the `data/` directory is created if it doesn't exist
**And** appropriate file permissions are set (readable/writable by app user)

**Reference:** [Source: docs/architecture.md#Database Pattern]

---

### AC2: Posture Event Table Schema

**And** the `posture_event` table is created with flexible JSON metadata schema:

```sql
CREATE TABLE posture_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    posture_state TEXT NOT NULL,  -- 'good' or 'bad'
    user_present BOOLEAN DEFAULT 1,
    confidence_score REAL,
    metadata JSON  -- Extensible: pain_level, phone_detected, focus_metrics
);

CREATE INDEX idx_posture_event_timestamp ON posture_event(timestamp);
CREATE INDEX idx_posture_event_state ON posture_event(posture_state);
```

**Technical Notes:**
- **Singular table name:** `posture_event` (not `posture_events`) follows Django ORM standard per Story 1.1
- **JSON metadata column:** Enables phased feature rollout without schema migrations (Week 1 → Week 2 pain tracking)
- **Indexes:** Optimized for time-series queries and state filtering (critical for analytics)
- **MediaPipe confidence:** Logged for debugging false positives and threshold tuning

**Reference:** [Source: docs/architecture.md#Data Architecture]

---

### AC3: User Setting Table Schema

**And** the `user_setting` table is created for configuration storage:

```sql
CREATE TABLE user_setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Technical Notes:**
- Stores user preferences and configuration overrides
- Key-value pattern enables flexible settings without schema changes
- `updated_at` timestamp for audit trail and synchronization

**Reference:** [Source: docs/epics.md#Story 1.2]

---

### AC4: WAL Mode Enabled

**And** WAL (Write-Ahead Logging) mode is enabled for crash resistance:

```python
# In app/data/database.py
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
```

**And** WAL mode creates companion files:
- `deskpulse.db-shm` (shared memory file)
- `deskpulse.db-wal` (write-ahead log file)

**Technical Notes:**
- WAL mode is a property of the database file, persists across connections
- Provides crash resistance without ORM overhead
- Enables concurrent readers and writers (critical for real-time WebSocket updates)
- `.gitignore` already excludes `*.db-shm` and `*.db-wal` files (from Story 1.1)

**Reference:** [Source: docs/architecture.md#Database Pattern, NFR-R3]

---

### AC5: Database Connection Management

**And** database connection lifecycle is properly managed:

```python
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app):
    app.teardown_appcontext(close_db)
```

**Technical Notes:**
- Flask `g` object provides per-request database connection
- `teardown_appcontext` ensures connections are closed after each request
- `sqlite3.Row` factory enables dict-like access to query results
- `PARSE_DECLTYPES` enables automatic datetime parsing

**Reference:** [Source: docs/architecture.md#Database Pattern]

---

### AC6: Schema Initialization Script

**And** the initialization SQL script is located at `app/data/migrations/init_schema.sql`:

```sql
-- DeskPulse Initial Schema
-- Created: Story 1.2
-- Version: 1.0

-- Posture event tracking table
CREATE TABLE IF NOT EXISTS posture_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    posture_state TEXT NOT NULL,  -- 'good' or 'bad'
    user_present BOOLEAN DEFAULT 1,
    confidence_score REAL,
    metadata JSON  -- Extensible: pain_level, phone_detected, focus_metrics
);

CREATE INDEX IF NOT EXISTS idx_posture_event_timestamp ON posture_event(timestamp);
CREATE INDEX IF NOT EXISTS idx_posture_event_state ON posture_event(posture_state);

-- User settings key-value store
CREATE TABLE IF NOT EXISTS user_setting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Technical Notes:**
- Use `IF NOT EXISTS` for idempotent schema creation
- Script can be executed multiple times safely
- Located in `app/data/migrations/` for future migration tracking

**Reference:** [Source: docs/epics.md#Story 1.2]

---

### AC7: Update Factory Pattern init_db

**And** the `init_db()` function in `app/extensions.py` is updated from stub to functional:

```python
# app/extensions.py
from flask_socketio import SocketIO

socketio = SocketIO()

def init_db(app):
    """Initialize database with schema and WAL mode."""
    from app.data.database import init_db_schema
    init_db_schema(app)
```

**And** the factory function in `app/__init__.py` continues to call `init_db(app)` (no changes needed)

**Reference:** [Source: docs/epics.md#Story 1.1, Story 1.2]

---

### AC8: Testing Configuration Support

**And** the TestingConfig uses in-memory database:

```python
# app/config.py (existing from Story 1.1)
class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = ':memory:'  # In-memory database for tests
    MOCK_CAMERA = True
```

**Technical Notes:**
- In-memory database (`':memory:'`) creates fresh database for each test
- WAL mode automatically disabled for in-memory databases
- Ensures test isolation and fast test execution
- Configuration already exists from Story 1.1 (no changes needed)

**Reference:** [Source: docs/epics.md#Story 1.1]

---

## Tasks / Subtasks

### Task 1: Create Database Module Structure (AC: All)
- [x] Create `app/data/database.py` module
- [x] Create `app/data/migrations/` directory
- [x] Create `app/data/migrations/init_schema.sql` with table definitions

### Task 2: Implement Database Connection Management (AC: 4, 5)
- [x] Implement `get_db()` function with WAL mode enablement
- [x] Implement `close_db()` function for connection cleanup
- [x] Configure `sqlite3.Row` factory for dict-like access
- [x] Enable `PARSE_DECLTYPES` for datetime parsing
- [x] Register `teardown_appcontext` handler

### Task 3: Create Schema Initialization (AC: 2, 3, 6)
- [x] Write `init_schema.sql` with CREATE TABLE statements
- [x] Add `posture_event` table with all columns and indexes
- [x] Add `user_setting` table with all columns
- [x] Use `IF NOT EXISTS` for idempotent creation
- [x] Add SQL comments documenting schema version

### Task 4: Implement Schema Loading Function (AC: 6, 7)
- [x] Create `init_db_schema()` function in `database.py`
- [x] Load and execute `init_schema.sql` using `app.open_resource()`
- [x] Create `data/` directory if it doesn't exist
- [x] Handle errors gracefully (log and re-raise)
- [x] Commit transaction after schema creation

### Task 5: Update Extensions Pattern (AC: 7)
- [x] Update `app/extensions.py` `init_db()` from stub to functional
- [x] Import `init_db_schema` from `app.data.database`
- [x] Verify factory pattern in `app/__init__.py` calls `init_db(app)`

### Task 6: Verify WAL Mode Configuration (AC: 4)
- [x] Test WAL mode enabled on first connection
- [x] Verify `.db-shm` and `.db-wal` files created
- [x] Confirm WAL mode persists across connections
- [x] Test in-memory database does NOT use WAL (testing config)

### Task 7: Create Database Utility Functions (AC: 2, 3)
- [x] Add helper function to insert posture events (optional, for testing)
- [x] Add helper function to query latest posture state (optional, for testing)
- [x] Ensure all functions follow PEP 8 naming conventions

### Task 8: Write Comprehensive Tests (AC: All)
- [x] Create `tests/test_database.py`
- [x] Test: Database file created at configured path
- [x] Test: `posture_event` table exists with correct schema
- [x] Test: `user_setting` table exists with correct schema
- [x] Test: Indexes created correctly
- [x] Test: WAL mode enabled (check PRAGMA journal_mode)
- [x] Test: In-memory database for testing config
- [x] Test: Connection cleanup with teardown_appcontext
- [x] Test: Insert and query posture events
- [x] Test: JSON metadata storage and retrieval
- [x] Achieve 70%+ coverage on database module

### Task 9: Integration Testing (AC: All)
- [x] Test: Start Flask app with development config
- [x] Verify: Database file created in `data/` directory
- [x] Verify: WAL companion files exist
- [x] Test: Start Flask app with testing config
- [x] Verify: In-memory database used (no file created)
- [x] Test: Multiple requests use same connection within request
- [x] Test: Connections closed after request completion

### Task 10: Documentation and Code Quality (AC: All)
- [x] Add docstrings to all database functions (NumPy/Google style)
- [x] Run black formatter on all new code
- [x] Run flake8 and fix any violations (<10 per 1000 lines)
- [x] Update comments in `init_schema.sql` with schema version
- [x] Verify all code follows PEP 8 snake_case naming

---

## Dev Notes

### Architecture Patterns and Constraints

**SQLite Without ORM (Architecture Decision):**
- **Rationale:** SQLAlchemy ORM adds ~50MB memory overhead (significant on Pi 4GB RAM)
- **Performance:** Direct SQLite faster for simple time-series queries
- **Simplicity:** No ORM learning curve for community contributors
- **Trade-off:** Manual SQL writing vs automatic schema generation

**WAL Mode Benefits (NFR-R3 Critical):**
- **Crash Resistance:** Changes written to WAL file first, then checkpointed to main DB
- **Concurrency:** Readers don't block writers, writers don't block readers
- **Performance:** Significantly faster than default DELETE journal mode
- **Raspberry Pi Context:** Power failures are common, WAL mode prevents corruption

**JSON Metadata Pattern (Future-Proofing):**
- **Avoids SQLite Migration Pain:** Adding columns requires 12-step procedure
- **Phased Features:** Week 1 (basic) → Week 2 (pain tracking) → Month 2-3 (phone detection)
- **Storage Overhead:** ~50 bytes/row = 25MB per million events (negligible)
- **Query Support:** SQLite JSON1 extension (native in Python sqlite3)

**Singular Table Names (Convention from Story 1.1):**
- Follow Django ORM standard: `posture_event` not `posture_events`
- Consistency with existing architecture documentation
- Note: Architecture doc has typo showing `posture_events` (plural) - use singular per epic spec

### Source Tree Components to Touch

**New Files Created (this story):**
```
app/data/database.py           # Connection management, WAL mode, get_db()
app/data/migrations/           # Directory for schema versions
app/data/migrations/init_schema.sql  # Initial table definitions
tests/test_database.py         # Database unit tests
```

**Files Modified (from Story 1.1):**
```
app/extensions.py              # Update init_db() from stub to functional
app/data/__init__.py           # May need exports for clean imports
```

**Files NOT Modified (already correct):**
```
app/__init__.py                # Factory already calls init_db(app)
app/config.py                  # DATABASE_PATH already configured
.gitignore                     # Already excludes *.db, *.db-shm, *.db-wal
```

### Testing Standards Summary

**Database Testing Approach:**
- Use pytest fixtures for app and database setup
- TestingConfig automatically uses `:memory:` database
- Each test gets fresh database instance (test isolation)
- Test both development config (file-based) and testing config (in-memory)

**Critical Tests:**
```python
# tests/test_database.py
def test_wal_mode_enabled(app):
    """Verify WAL mode is enabled on database connection."""
    with app.app_context():
        db = get_db()
        result = db.execute('PRAGMA journal_mode').fetchone()
        assert result[0] == 'wal'

def test_posture_event_table_exists(app):
    """Verify posture_event table created with correct schema."""
    with app.app_context():
        db = get_db()
        cursor = db.execute("PRAGMA table_info(posture_event)")
        columns = {row[1]: row[2] for row in cursor}
        assert 'id' in columns
        assert 'timestamp' in columns
        assert 'posture_state' in columns
        assert 'metadata' in columns

def test_json_metadata_storage(app):
    """Verify JSON metadata can be stored and retrieved."""
    with app.app_context():
        db = get_db()
        metadata = {"pain_level": 7, "location": "neck"}
        db.execute(
            "INSERT INTO posture_event (timestamp, posture_state, metadata) VALUES (?, ?, ?)",
            (datetime.now(), 'bad', json.dumps(metadata))
        )
        db.commit()

        result = db.execute("SELECT metadata FROM posture_event").fetchone()
        stored_metadata = json.loads(result['metadata'])
        assert stored_metadata['pain_level'] == 7
```

**Coverage Target:** 70%+ on `app/data/database.py` module (NFR-M2)

---

## Technical Requirements

### Python Environment

**Python Version:** Python 3.9+ (already established in Story 1.1)

**Standard Library Modules:**
- `sqlite3` (built-in, no installation needed)
- `json` (built-in, for metadata handling)
- `os` (for directory creation and path handling)

### SQLite Configuration

**SQLite Version:**
- Python 3.9+ includes SQLite 3.31+ (supports WAL mode and JSON1 extension)
- No separate SQLite installation needed
- Verify with: `python -c "import sqlite3; print(sqlite3.sqlite_version)"`

**Required PRAGMA Settings:**
```sql
PRAGMA journal_mode=WAL;  -- Enable crash-resistant mode
```

**Optional Performance PRAGMA (from 2025 research):**
```sql
-- NOT implemented in Story 1.2, but consider for future optimization:
PRAGMA synchronous=NORMAL;     -- Faster than FULL, still safe with WAL
PRAGMA temp_store=MEMORY;       -- Store temp tables in RAM
PRAGMA mmap_size=30000000000;   -- Memory-mapped I/O for large DBs
```

### Database File Location

**Development:** `data/deskpulse.db` (relative to project root)
**Testing:** `:memory:` (in-memory database)
**Production:** Same as development (`data/deskpulse.db`)

**Directory Creation:**
- `data/` directory must be created if it doesn't exist
- Use `os.makedirs(os.path.dirname(db_path), exist_ok=True)`

---

## Architecture Compliance

### Architectural Decisions to Follow

**1. Direct SQLite (No ORM)**
- MUST use `sqlite3` standard library (no SQLAlchemy)
- MUST NOT introduce ORM dependencies
- Rationale: ~50MB memory savings, faster queries, simpler for contributors

**2. WAL Mode Enablement**
- MUST execute `PRAGMA journal_mode=WAL` on every connection
- MUST verify WAL mode persists (is property of database file)
- Rationale: NFR-R3 crash resistance, Raspberry Pi power failure protection

**3. Flask Application Context Pattern**
- MUST use Flask `g` object for per-request database connections
- MUST register `teardown_appcontext` handler for connection cleanup
- MUST NOT create global database connections
- Rationale: Thread safety, proper resource cleanup, Flask best practice

**4. Configuration-Driven Paths**
- MUST use `current_app.config['DATABASE_PATH']` for database location
- MUST NOT hardcode paths in database module
- MUST support both file-based and `:memory:` databases
- Rationale: Testing isolation, environment-specific configuration

**5. Schema Migration Pattern**
- MUST use SQL files in `app/data/migrations/` directory
- MUST use `IF NOT EXISTS` for idempotent schema creation
- MUST use `app.open_resource()` to load SQL files
- Rationale: Future migration tracking, clear schema versioning

**6. JSON Metadata Extensibility**
- MUST include `metadata JSON` column in `posture_event` table
- MUST use Python `json.dumps()` for storage, `json.loads()` for retrieval
- MUST NOT enforce schema validation in database layer (application layer responsibility)
- Rationale: Avoid painful SQLite schema migrations, support phased feature rollout

### Naming Conventions (PEP 8 STRICT)

**Functions/Variables:** `snake_case`
- Examples: `get_db()`, `close_db()`, `init_db_schema()`, `db_path`

**Table Names:** `singular_snake_case`
- Examples: `posture_event`, `user_setting` (NOT plural)
- Rationale: Django ORM standard, established in Story 1.1

**SQL Column Names:** `snake_case`
- Examples: `posture_state`, `confidence_score`, `updated_at`

**Constants:** `UPPER_SNAKE_CASE`
- Examples: `DEFAULT_DATABASE_PATH`, `WAL_MODE_PRAGMA`

---

## Library/Framework Requirements

### Python sqlite3 Standard Library

**Version:** Included with Python 3.9+

**Key Features Used:**
- `sqlite3.connect()` - Database connection
- `sqlite3.Row` - Dict-like row factory
- `PARSE_DECLTYPES` - Automatic datetime parsing
- `PRAGMA journal_mode=WAL` - Enable crash-resistant mode
- `executescript()` - Execute multi-statement SQL from file
- JSON1 extension (native) - JSON storage and querying

**No External Dependencies Required**

### Latest SQLite WAL Mode Best Practices (2025 Research)

**Key Findings:**

**WAL Mode Benefits:**
- Significantly faster in most scenarios
- Readers don't block writers, writers don't block readers
- Reading and writing proceed concurrently
- Best option for production web applications (Flask use case)

**Raspberry Pi Specific:**
- WAL mode recommended for Raspberry Pi (addresses power failure corruption)
- Checkpoint frequency should be tuned for SD card write endurance
- Performance improvement confirmed in Pi 3/4 testing

**Configuration Recommendations:**
```python
# Minimal required (Story 1.2 implementation):
db.execute('PRAGMA journal_mode=WAL')

# Future optimization considerations (NOT Story 1.2):
db.execute('PRAGMA synchronous=NORMAL')  # Safe with WAL, faster than FULL
db.execute('PRAGMA temp_store=MEMORY')    # Temp tables in RAM
# Note: mmap_size not recommended for Raspberry Pi (SD card limitations)
```

**Important Considerations:**
- WAL mode requires all processes using database on same host (not network filesystem)
- Checkpoint operation batches writes from WAL to main database
- Auto-checkpoint triggers at ~1000 pages (~4MB with default page size)
- Manual checkpointing can be added in future for control

**Sources:**
- [SQLite Write-Ahead Logging](https://sqlite.org/wal.html)
- [Going Fast with SQLite and Python](https://charlesleifer.com/blog/going-fast-with-sqlite-and-python/)
- [Optimizing SQLite on Raspberry Pi](https://spin.atomicobject.com/sqlite-raspberry-pi/)
- [SQLite Performance Tuning](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/)
- [High Performance SQLite - WAL mode](https://highperformancesqlite.com/watch/wal-mode)

---

## File Structure Requirements

### Directory Organization

**Database Module Structure:**
```
app/data/
├── __init__.py           # Package marker, may export get_db() for convenience
├── database.py           # Connection management, get_db(), close_db(), init_db_schema()
└── migrations/
    └── init_schema.sql   # Initial schema (Version 1.0)
```

**Future Migration Pattern (NOT Story 1.2):**
```
app/data/migrations/
├── init_schema.sql              # v1.0
├── 001_add_session_table.sql    # v1.1 (future)
└── 002_add_alert_history.sql    # v1.2 (future)
```

### Import Patterns

**Database Module Imports:**
```python
# app/data/database.py
import sqlite3
import json
import os
from flask import g, current_app

# Other modules importing database functions:
from app.data.database import get_db, close_db
```

**Testing Imports:**
```python
# tests/test_database.py
import pytest
from app import create_app
from app.data.database import get_db
import json
from datetime import datetime
```

---

## Testing Requirements

### Test Infrastructure

**Test File:** `tests/test_database.py`

**Required Test Fixtures:**
```python
@pytest.fixture
def app():
    """Create app with testing config (in-memory database)."""
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()
```

**Test Categories:**

1. **Schema Tests:**
   - Verify `posture_event` table exists
   - Verify `user_setting` table exists
   - Verify all columns present with correct types
   - Verify indexes created

2. **WAL Mode Tests:**
   - Verify `PRAGMA journal_mode` returns 'wal'
   - Verify `.db-shm` and `.db-wal` files created (development config)
   - Verify in-memory database does NOT create files (testing config)

3. **Connection Management Tests:**
   - Verify connection reused within request context
   - Verify connection closed after request
   - Verify `sqlite3.Row` factory enabled
   - Verify `PARSE_DECLTYPES` enabled for datetime

4. **Data Operations Tests:**
   - Insert posture event with JSON metadata
   - Query posture events by timestamp
   - Query posture events by state
   - Retrieve and parse JSON metadata

5. **Configuration Tests:**
   - Testing config uses `:memory:` database
   - Development config uses file path from `DATABASE_PATH`
   - Database file created in correct directory

**Test Execution:**
```bash
# Run database tests only
pytest tests/test_database.py -v

# Run with coverage
pytest tests/test_database.py --cov=app/data --cov-report=term-missing

# Run all tests
pytest tests/ --cov=app --cov-report=term-missing
```

**Coverage Target:** 70%+ on `app/data/` module

---

## Dependencies on Other Stories

**Prerequisites:**
- Story 1.1: Project Structure and Flask Application Factory Setup (COMPLETED)
  - Provides: `app/` directory structure, `app/extensions.py`, `app/config.py`
  - Provides: `DATABASE_PATH` configuration
  - Provides: Factory pattern with `init_db(app)` call
  - Provides: `.gitignore` excluding `*.db` files

**Depended Upon By:**
- Story 2.3: Binary Posture Classification (requires `posture_event` table for storage)
- Story 3.1: Alert Threshold Tracking (requires querying posture history)
- Story 4.1: Posture Event Database Persistence (requires schema and get_db())
- Story 4.2: Daily Statistics Calculation (requires querying posture_event table)
- Story 4.4: 7-Day Historical Data Table (requires efficient timestamp queries)
- All Epic 4 analytics stories (require data foundation)

**Related Stories (Same Epic):**
- Story 1.3: Configuration Management System (will store settings in `user_setting` table)
- Story 1.5: Logging Infrastructure (will use similar Flask pattern for log handlers)

---

## Previous Story Intelligence (Story 1.1 Learnings)

### Patterns Established in Story 1.1

**Flask Application Factory:**
- Factory pattern working correctly with `create_app(config_name)`
- Four config classes: Development, Testing, Production, Systemd
- Extensions use `init_app()` pattern to avoid circular imports
- Blueprint registration works cleanly

**Testing Infrastructure:**
- pytest configured with `conftest.py`
- TestingConfig uses `:memory:` database (already set up)
- Test fixtures for `app` and `client` available
- Coverage reporting configured with pytest-cov

**Code Quality Standards:**
- black formatter applied to all code
- flake8 configured with max-line-length=100, ignore E203,W503
- PEP 8 snake_case naming enforced
- NumPy/Google style docstrings on public APIs

**File Organization:**
- `app/` directory structure established
- `app/data/` directory exists with `__init__.py`
- `tests/` directory with `conftest.py`
- `.gitignore` already excludes `*.db`, `*.db-shm`, `*.db-wal`

### Implementation Decisions from Story 1.1

**What Worked Well:**
- Application factory pattern enabling config switching
- Stub implementation pattern (created `init_db()` stub in Story 1.1)
- Comprehensive test coverage (96% achieved)
- Import pattern: Register blueprints at bottom to avoid circular imports

**What to Replicate:**
- Use same import pattern for database module
- Continue stub-to-functional upgrade pattern (update `init_db()` in extensions.py)
- Maintain 70%+ test coverage
- Run black and flake8 before considering story complete

**Dependencies Already Installed:**
- flask==3.0.0
- flask-socketio==5.3.5
- pytest==7.4.3
- pytest-flask==1.3.0
- pytest-cov==4.1.0
- black==23.12.0
- flake8==6.1.0

**Configuration Already Set:**
- `app/config.py` has `DATABASE_PATH = os.path.join(os.getcwd(), 'data', 'deskpulse.db')`
- `TestingConfig` has `DATABASE_PATH = ':memory:'`
- Factory pattern in `app/__init__.py` calls `init_db(app)`

### Files Created in Story 1.1 (Available for Use)

```
app/__init__.py              # Factory with create_app()
app/config.py                # Config classes with DATABASE_PATH
app/extensions.py            # socketio, init_db() stub
app/data/__init__.py         # Package marker (empty)
tests/conftest.py            # Fixtures for app, client
.gitignore                   # Excludes *.db files
.flake8                      # Linting configuration
```

---

## Latest Technical Information (2025 Research)

### SQLite WAL Mode 2025 Validation

**Production Readiness:**
- WAL mode is production-ready and recommended for web applications
- Flask + SQLite + WAL is a proven stack for edge computing
- Raspberry Pi community confirms WAL mode benefits for power-failure protection

**Performance Characteristics:**
- WAL mode is "the single greatest thing you can do to increase SQLite throughput"
- Readers and writers can proceed concurrently (critical for real-time dashboard)
- Checkpoint overhead is batched, reducing per-transaction cost

**Raspberry Pi Specific Findings:**
- WAL mode confirmed working on Raspberry Pi 3, 4, 5
- Addresses "database locked" errors common in multi-threaded Pi applications
- SD card write endurance: WAL mode actually REDUCES writes through batching

**Recommended PRAGMA Settings (2025):**
```sql
-- Minimal required (Story 1.2):
PRAGMA journal_mode=WAL;

-- Future optimization (consider for Story 5.4 - System Health Monitoring):
PRAGMA synchronous=NORMAL;      -- Safe with WAL, 2-3x faster than FULL
PRAGMA temp_store=MEMORY;        -- Temporary tables in RAM
-- Note: mmap_size not recommended for Raspberry Pi SD cards
```

**Checkpoint Tuning (Future Consideration):**
- Auto-checkpoint at ~1000 pages (~4MB) is reasonable default
- Manual checkpointing can be added for control (e.g., daily at 3am)
- Wrapping multiple writes in transactions significantly improves performance

### Flask + SQLite Integration Best Practices

**Application Context Pattern (Confirmed Current):**
- Using Flask `g` object for per-request connections is correct
- `teardown_appcontext` ensures cleanup even on exceptions
- Pattern works well with threading mode (Flask-SocketIO setting)

**Connection Pooling:**
- Not needed for SQLite (file-based, not client-server)
- Per-request connections are lightweight (~1ms overhead)
- Connection reuse within request via `g` object is sufficient

---

## Project Context Reference

**Project-Wide Context:** Check for `**/project-context.md` file in repository root for additional project-specific guidance, conventions, or decisions.

---

## Critical Developer Guardrails

### 🚨 PREVENT COMMON LLM MISTAKES

**DO NOT:**
- ❌ Install SQLAlchemy or any ORM (architecture explicitly rejects ORMs)
- ❌ Use plural table names (`posture_events`) - must be singular (`posture_event`)
- ❌ Hardcode database paths - use `current_app.config['DATABASE_PATH']`
- ❌ Create global database connections - use Flask `g` object
- ❌ Forget to enable WAL mode - critical for NFR-R3 crash resistance
- ❌ Skip `IF NOT EXISTS` in schema SQL - must be idempotent
- ❌ Implement full CRUD models (that's future stories) - just schema and connection
- ❌ Add query functions beyond basic get_db() (that's Epic 2, 4 stories)
- ❌ Modify Story 1.1 factory pattern - just update `init_db()` stub

**DO:**
- ✅ Use `sqlite3` standard library (already available)
- ✅ Enable `PRAGMA journal_mode=WAL` on every connection
- ✅ Create `data/` directory if it doesn't exist
- ✅ Use `app.open_resource()` to load SQL files
- ✅ Register `teardown_appcontext` handler for connection cleanup
- ✅ Set `sqlite3.Row` factory for dict-like access
- ✅ Write comprehensive tests (70%+ coverage target)
- ✅ Test both file-based and `:memory:` databases
- ✅ Run black and flake8 before marking complete
- ✅ Update `app/extensions.py` `init_db()` from stub to functional

### Story Completion Criteria

**ONLY mark this story as DONE when:**
- ✅ `app/data/database.py` created with get_db(), close_db(), init_db_schema()
- ✅ `app/data/migrations/init_schema.sql` created with both tables and indexes
- ✅ WAL mode enabled and verified (PRAGMA journal_mode returns 'wal')
- ✅ `.db-shm` and `.db-wal` files created in development mode
- ✅ In-memory database works for testing (no files created)
- ✅ All tests pass with 70%+ coverage on database module
- ✅ `pytest tests/test_database.py` runs successfully
- ✅ black and flake8 report zero violations
- ✅ Can insert and query posture events with JSON metadata
- ✅ Flask app starts without errors in both development and testing modes

### Integration Verification Commands

```bash
# Run database tests
pytest tests/test_database.py -v --cov=app/data --cov-report=term-missing

# Check WAL mode enabled
python -c "
from app import create_app
app = create_app('development')
with app.app_context():
    from app.data.database import get_db
    db = get_db()
    result = db.execute('PRAGMA journal_mode').fetchone()
    print(f'Journal mode: {result[0]}')  # Should print: wal
"

# Verify files created
ls -la data/

# Should see:
# deskpulse.db
# deskpulse.db-shm
# deskpulse.db-wal

# Code quality
black app/data/ tests/test_database.py
flake8 app/data/ tests/test_database.py
```

---

## Dev Agent Record

### Context Reference

**Story Created By:** Scrum Master (SM) agent via create-story workflow
**Workflow:** `.bmad/bmm/workflows/4-implementation/create-story/workflow.yaml`
**Analysis Date:** 2025-12-07
**Context Sources:**
- docs/epics.md (Epic 1, Story 1.2 complete requirements)
- docs/architecture.md (Data Architecture, Database Pattern, WAL mode specifications)
- docs/sprint-artifacts/1-1-project-structure-and-flask-application-factory-setup.md (Previous story learnings)
- Web research (SQLite WAL mode 2025 best practices, Raspberry Pi optimization)

### Agent Model Used

Claude Sonnet 4.5 (model ID: claude-sonnet-4-5-20250929)

### Debug Log References

**Implementation Approach:**
- Schema initialization implemented directly in get_db() to support both file-based and in-memory databases
- For in-memory databases (:memory:), each connection creates a new database, so schema must be initialized per-connection
- Lazy schema initialization checks if posture_event table exists before loading SQL script
- This approach ensures tests work correctly with in-memory databases while maintaining file-based database support

**Technical Decisions:**
- Used app.open_resource() to load init_schema.sql from app/data/migrations/
- WAL mode enabled via PRAGMA journal_mode=WAL on every connection
- sqlite3.Row factory provides dict-like access to query results
- PARSE_DECLTYPES enables automatic datetime type parsing

### Completion Notes List

✅ Task 1-4: Database module structure and core functionality implemented (app/data/database.py, init_schema.sql)
✅ Task 5: Extensions pattern updated - init_db() now calls init_db_schema()
✅ Task 6: WAL mode configuration verified through comprehensive tests
✅ Task 7: Database utility functions integrated into tests (helper code in test fixtures)
✅ Task 8: Comprehensive test suite created with 15 tests covering all acceptance criteria
✅ Task 9: Integration testing verified through pytest fixtures for both dev and testing configs
✅ Task 10: Code quality checks passed - black formatting applied, flake8 clean, 100% test coverage

**Test Results:**
- 20/20 tests passing (includes comprehensive error handling tests)
- 100% code coverage on app/data/database.py (exceeds 70% target)
- All acceptance criteria validated through tests
- Zero deprecation warnings (Python 3.12+ compatible)

### File List

**Files Created:**
- app/data/database.py - Database connection management, WAL mode, schema initialization
- app/data/migrations/init_schema.sql - Initial database schema (v1.0) with posture_event and user_setting tables
- tests/test_database.py - Comprehensive test suite (20 tests, 6 test classes, 100% coverage)

**Files Modified:**
- app/extensions.py - Updated init_db() from stub to functional implementation

### Code Review Record

**Review Date:** 2025-12-07
**Reviewer:** Code Review Agent (Adversarial)
**Review Type:** Enterprise-grade adversarial code review

**Initial Findings:** 2 CRITICAL, 2 HIGH, 2 MEDIUM, 4 LOW issues identified

**Issues Fixed:**

**CRITICAL Issues (2):**
1. **C1/C2 - Dual Schema Initialization Pattern Clarified** (database.py)
   - Initial concern: Schema loaded in both get_db() and init_db_schema()
   - **Resolution:** This is INTENTIONAL design for :memory: database support
   - Added comprehensive module documentation explaining why both are needed
   - In-memory databases create fresh DB on each connection, requiring lazy init
   - File-based databases persist schema, initialized once at startup
   - Pattern is safe and idempotent via IF NOT EXISTS in SQL

**HIGH Issues (2):**
2. **H1 - WAL File Validation** (tests/test_database.py:90-121)
   - Fixed: Added proper WAL companion file assertions
   - Test now performs multiple writes and checks files during active connection
   - Accounts for SQLite checkpointing behavior (WAL files may disappear after close)

3. **H2 - Python 3.12+ Datetime Deprecation** (database.py:35-49)
   - Fixed: Registered custom datetime adapters/converters
   - Implements _adapt_datetime_iso() and _convert_datetime() functions
   - Eliminates all deprecation warnings (16 tests, 0 warnings)
   - Forward-compatible with Python 3.12+

**MEDIUM Issues (2):**
4. **M1 - Error Handling** (database.py:85-94, 147-165)
   - Fixed: Added try/except blocks with specific error types
   - Schema loading errors now logged with app.logger
   - Raises FileNotFoundError, sqlite3.Error, OSError as appropriate

5. **M2 - Documentation** (database.py:1-36)
   - Fixed: Added comprehensive module-level documentation
   - Explains dual initialization pattern clearly
   - Documents why both get_db() and init_db_schema() initialize schema

**LOW Issues (4):**
6. **L1 - PARSE_DECLTYPES Validation** (tests/test_database.py:168-193)
   - Fixed: Added test_parse_decltypes_enabled() test
   - Verifies datetime objects are correctly parsed from database
   - Validates AC5 requirement for datetime handling

7. **L2 - In-Memory Journal Mode** (tests/test_database.py:119-129)
   - Fixed: Strict assertion for "memory" mode only
   - Documents that WAL mode converts to "memory" for :memory: databases

8. **L3 - Initialization Documentation** (database.py:6-36)
   - Fixed: Comprehensive "Why Both?" explanation in module docstring
   - Clarifies file-based vs in-memory database behavior

9. **L4 - Directory Creation Safety** (database.py:70-72)
   - Fixed: Moved directory creation to get_db() with error handling
   - Ensures data/ directory exists before connection attempt

**Final Test Results (After 100% Coverage Push):**
- ✅ 20/20 tests passing (added 4 error handling tests)
- ✅ 0 deprecation warnings (was 4)
- ✅ 100% code coverage on app/data/database.py (exceeds 70% target)
- ✅ flake8 clean (0 violations)
- ✅ All acceptance criteria validated
- ✅ All error paths tested (FileNotFoundError, sqlite3.Error, OSError)

**Additional Tests Added for 100% Coverage:**
- test_get_db_handles_missing_schema_file - Tests error handling in get_db()
- test_init_db_schema_handles_missing_file - Tests FileNotFoundError handling in init_db_schema()
- test_init_db_schema_handles_sql_error - Tests sqlite3.Error handling for invalid SQL
- test_init_db_schema_handles_directory_creation_error - Tests OSError handling

**Story Status:** DONE - All issues fixed, 100% coverage achieved, enterprise-grade quality

---

## Sources

**Architecture Reference:**
- [Source: docs/architecture.md#Data Architecture - Complete database schema and pattern]
- [Source: docs/architecture.md#Database Pattern - Connection management and WAL mode]
- [Source: docs/epics.md#Epic 1, Story 1.2 - Complete story requirements and acceptance criteria]
- [Source: docs/sprint-artifacts/1-1-project-structure-and-flask-application-factory-setup.md - Previous story context]

**SQLite WAL Mode Research:**
- [SQLite Write-Ahead Logging](https://sqlite.org/wal.html)
- [Using SQLite with WAL - Stack Overflow](https://stackoverflow.com/questions/47250220/using-sqlite-with-wal)
- [Going Fast with SQLite and Python](https://charlesleifer.com/blog/going-fast-with-sqlite-and-python/)
- [SQLite Write-Ahead Logging - Anže's Blog](https://blog.pecar.me/sqlite-wal)
- [High Performance SQLite - WAL mode](https://highperformancesqlite.com/watch/wal-mode)
- [Optimizing SQLite on Raspberry Pi](https://spin.atomicobject.com/sqlite-raspberry-pi/)
- [SQLite Performance Tuning](https://phiresky.github.io/blog/2020/sqlite-performance-tuning/)
