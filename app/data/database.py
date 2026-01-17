"""Database connection management and initialization.

This module provides SQLite database connection management using Flask's
application context pattern with WAL mode for crash resistance.

Initialization Pattern:
-----------------------
Schema initialization uses a dual approach to support both file-based and
in-memory databases:

1. Application Startup (app/extensions.py):
   - init_db_schema(app) is called once during app creation
   - Loads and executes data/migrations/init_schema.sql
   - Creates tables and indexes using IF NOT EXISTS (idempotent)
   - Registers teardown handler for connection cleanup
   - Primary initialization for file-based databases

2. Per-Request Connection (via get_db()):
   - Each request gets a fresh connection via Flask's g object
   - WAL mode enabled for crash resistance
   - Row factory configured for dict-like access
   - Checks if schema exists; if not, loads init_schema.sql (idempotent)
   - This lazy initialization is CRITICAL for :memory: databases, which
     create a fresh database on each connection

Why Both?
- File-based databases: Schema persists, init_db_schema() runs once at startup
- In-memory databases (:memory:): Each connection is a fresh DB, get_db() must
  initialize schema every time
- IF NOT EXISTS in SQL makes this safe and idempotent in both cases

This pattern ensures:
- In-memory databases work correctly for testing
- File-based databases initialize efficiently at startup
- No runtime errors from missing schema
- Minimal performance impact (table existence check is fast)
"""

import logging
import sqlite3
import os
from datetime import datetime
from flask import g, current_app

# Hierarchical logger for database operations (AC2)
logger = logging.getLogger("deskpulse.db")


# Python 3.12+ compatibility: Register custom datetime adapters/converters
# to avoid deprecation warnings for the default datetime adapter
def _adapt_datetime_iso(val):
    """Adapt datetime to ISO 8601 format for SQLite storage."""
    return val.isoformat()


def _convert_datetime(val):
    """Convert ISO 8601 datetime string from SQLite to Python datetime."""
    return datetime.fromisoformat(val.decode())


# Register custom adapters and converters (Python 3.12+ compatibility)
sqlite3.register_adapter(datetime, _adapt_datetime_iso)
sqlite3.register_converter("DATETIME", _convert_datetime)


def get_db():
    """Get database connection for current request.

    Creates a new connection if one doesn't exist in the Flask g object.
    Enables WAL mode for crash resistance and configures row factory
    for dict-like access.

    For in-memory databases (:memory:), the schema is initialized on every
    connection since each connection creates a fresh database. For file-based
    databases, schema is typically initialized once by init_db_schema() during
    startup, but this function will initialize it if needed (idempotent).

    Returns:
        sqlite3.Connection: Database connection with Row factory.
    """
    if "db" not in g:
        db_path = current_app.config["DATABASE_PATH"]

        # Create data directory if it doesn't exist (for file-based databases)
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        # Enable WAL mode for crash resistance (NFR-R3)
        g.db.execute("PRAGMA journal_mode=WAL")
        logger.debug("Database connection opened: path=%s", db_path)

        # Initialize schema if not already done (idempotent via IF NOT EXISTS)
        # Critical for :memory: databases which are fresh on each connection
        # Also runs if new tables (like achievement_type) are missing from existing DB
        cursor = g.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posture_event'"
        )
        posture_table_exists = cursor.fetchone() is not None

        cursor = g.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='achievement_type'"
        )
        achievement_table_exists = cursor.fetchone() is not None

        # Run schema if core table missing OR if new achievement tables missing
        if not posture_table_exists or not achievement_table_exists:
            try:
                # Load and execute schema SQL (uses IF NOT EXISTS, safe to re-run)
                with current_app.open_resource(
                    "data/migrations/init_schema.sql", mode="r"
                ) as f:
                    g.db.executescript(f.read())
                g.db.commit()
                if not achievement_table_exists:
                    logger.info("Achievement tables created (schema migration)")
            except Exception as e:
                logger.error("Failed to initialize schema in get_db(): %s", e)
                raise

    return g.db


def close_db(e=None):
    """Close database connection for current request.

    Args:
        e: Exception that triggered teardown (optional).
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()
        logger.debug("Database connection closed")


def init_db_schema(app):
    """Initialize database schema from SQL file.

    This function should be called once during application startup (typically
    from app/extensions.py init_db()). It loads and executes the initial schema
    SQL file to create tables and indexes. Uses IF NOT EXISTS for idempotent
    schema creation.

    The schema is loaded from app/data/migrations/init_schema.sql and executed
    within an application context. The data directory is created if needed for
    file-based databases.

    Args:
        app: Flask application instance.

    Raises:
        FileNotFoundError: If init_schema.sql is missing.
        sqlite3.Error: If schema SQL has syntax errors or execution fails.
    """
    # Register teardown handler for connection cleanup
    app.teardown_appcontext(close_db)

    # Create data directory if it doesn't exist (for file-based databases)
    db_path = app.config["DATABASE_PATH"]
    if db_path != ":memory:":
        try:
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        except OSError as e:
            logger.error("Failed to create database directory: %s", e)
            raise

    # Initialize schema within app context
    with app.app_context():
        db = get_db()
        try:
            with app.open_resource("data/migrations/init_schema.sql", mode="r") as f:
                schema_sql = f.read()
            db.executescript(schema_sql)
            db.commit()
            logger.info("Database schema initialized successfully")
        except FileNotFoundError:
            logger.error("Schema file not found: data/migrations/init_schema.sql")
            raise
        except sqlite3.Error as e:
            logger.error("Failed to initialize database schema: %s", e)
            raise
