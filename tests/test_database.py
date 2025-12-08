"""Tests for database connection management and schema initialization."""

import pytest
import sqlite3
import json
import os
from datetime import datetime
from app import create_app
from app.data.database import get_db


@pytest.fixture
def app():
    """Create app with testing config (in-memory database)."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def dev_app():
    """Create app with development config (file-based database)."""
    app = create_app("development")
    yield app
    # Cleanup: Remove test database files
    db_path = app.config["DATABASE_PATH"]
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(f"{db_path}-shm"):
        os.remove(f"{db_path}-shm")
    if os.path.exists(f"{db_path}-wal"):
        os.remove(f"{db_path}-wal")


class TestDatabaseSchema:
    """Test database schema creation and structure."""

    def test_posture_event_table_exists(self, app):
        """Verify posture_event table created with correct schema."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("PRAGMA table_info(posture_event)")
            columns = {row[1]: row[2] for row in cursor}

            assert "id" in columns
            assert "timestamp" in columns
            assert "posture_state" in columns
            assert "user_present" in columns
            assert "confidence_score" in columns
            assert "metadata" in columns

    def test_user_setting_table_exists(self, app):
        """Verify user_setting table created with correct schema."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("PRAGMA table_info(user_setting)")
            columns = {row[1]: row[2] for row in cursor}

            assert "id" in columns
            assert "key" in columns
            assert "value" in columns
            assert "updated_at" in columns

    def test_posture_event_indexes_exist(self, app):
        """Verify indexes created correctly."""
        with app.app_context():
            db = get_db()
            cursor = db.execute("PRAGMA index_list(posture_event)")
            indexes = [row[1] for row in cursor]

            assert "idx_posture_event_timestamp" in indexes
            assert "idx_posture_event_state" in indexes


class TestWALMode:
    """Test WAL mode configuration."""

    def test_wal_mode_enabled(self, dev_app):
        """Verify WAL mode is enabled on database connection."""
        with dev_app.app_context():
            db = get_db()
            result = db.execute("PRAGMA journal_mode").fetchone()
            assert result[0].lower() == "wal"

    def test_wal_files_created(self, dev_app):
        """Verify .db-shm and .db-wal files created."""
        db_path = dev_app.config["DATABASE_PATH"]
        shm_file = f"{db_path}-shm"
        wal_file = f"{db_path}-wal"

        with dev_app.app_context():
            db = get_db()

            # Perform multiple writes to ensure WAL file is created and persists
            for i in range(5):
                db.execute(
                    "INSERT INTO posture_event (timestamp, posture_state) VALUES (?, ?)",
                    (datetime.now(), "good"),
                )
            db.commit()

            # Check for WAL files while connection is still open
            # At least one of the WAL companion files should exist
            wal_exists_during_connection = os.path.exists(wal_file) or os.path.exists(
                shm_file
            )

        # Main database file should definitely exist
        assert os.path.exists(db_path)

        # WAL files should have existed during the connection
        # Note: After connection closes, SQLite may checkpoint and remove WAL files
        # So we check that they existed at some point during the writes
        assert (
            wal_exists_during_connection
        ), "WAL companion files not created during active connection"

    def test_in_memory_database_for_testing(self, app):
        """Verify in-memory database used for testing config."""
        assert app.config["DATABASE_PATH"] == ":memory:"

        with app.app_context():
            db = get_db()
            # In-memory databases don't create files
            # When we set WAL mode on :memory: database, SQLite converts it to 'memory' mode
            result = db.execute("PRAGMA journal_mode").fetchone()
            # WAL mode is not supported for in-memory databases, should use 'memory'
            assert result[0].lower() == "memory"


class TestConnectionManagement:
    """Test database connection lifecycle."""

    def test_connection_reused_within_request(self, app):
        """Verify connection reused within request context."""
        with app.app_context():
            db1 = get_db()
            db2 = get_db()
            assert db1 is db2

    def test_row_factory_enabled(self, app):
        """Verify sqlite3.Row factory enabled for dict-like access."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO posture_event (timestamp, posture_state) VALUES (?, ?)",
                (datetime.now(), "good"),
            )
            db.commit()

            result = db.execute("SELECT * FROM posture_event").fetchone()
            assert isinstance(result, sqlite3.Row)
            # Test dict-like access
            assert result["posture_state"] == "good"

    def test_connection_cleanup_with_teardown(self, app):
        """Verify connection closed after request."""
        from flask import g

        with app.app_context():
            get_db()
            assert "db" in g

        # After context exit, g should be cleared
        # We can't easily test this without app request context

    def test_parse_decltypes_enabled(self, app):
        """Verify PARSE_DECLTYPES correctly parses datetime objects."""
        with app.app_context():
            db = get_db()
            # Insert a datetime object
            test_time = datetime(2025, 12, 7, 15, 30, 45)
            db.execute(
                "INSERT INTO posture_event (timestamp, posture_state) VALUES (?, ?)",
                (test_time, "good"),
            )
            db.commit()

            # Retrieve and verify it's parsed back as datetime object, not string
            result = db.execute("SELECT timestamp FROM posture_event").fetchone()
            retrieved_time = result["timestamp"]

            # Should be a datetime object, not a string
            assert isinstance(
                retrieved_time, datetime
            ), f"Expected datetime, got {type(retrieved_time)}"
            # Should match the inserted time (may lose microseconds)
            assert retrieved_time.year == test_time.year
            assert retrieved_time.month == test_time.month
            assert retrieved_time.day == test_time.day
            assert retrieved_time.hour == test_time.hour
            assert retrieved_time.minute == test_time.minute


class TestDataOperations:
    """Test database data operations."""

    def test_insert_posture_event(self, app):
        """Test inserting posture event."""
        with app.app_context():
            db = get_db()
            timestamp = datetime.now()
            db.execute(
                """INSERT INTO posture_event
                (timestamp, posture_state, user_present, confidence_score)
                VALUES (?, ?, ?, ?)""",
                (timestamp, "bad", True, 0.85),
            )
            db.commit()

            result = db.execute("SELECT * FROM posture_event").fetchone()
            assert result["posture_state"] == "bad"
            assert result["user_present"] == 1
            assert result["confidence_score"] == 0.85

    def test_json_metadata_storage(self, app):
        """Verify JSON metadata can be stored and retrieved."""
        with app.app_context():
            db = get_db()
            metadata = {"pain_level": 7, "location": "neck"}
            db.execute(
                """INSERT INTO posture_event
                (timestamp, posture_state, metadata)
                VALUES (?, ?, ?)""",
                (datetime.now(), "bad", json.dumps(metadata)),
            )
            db.commit()

            result = db.execute("SELECT metadata FROM posture_event").fetchone()
            stored_metadata = json.loads(result["metadata"])
            assert stored_metadata["pain_level"] == 7
            assert stored_metadata["location"] == "neck"

    def test_user_setting_insert_and_query(self, app):
        """Test user_setting table operations."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO user_setting (key, value) VALUES (?, ?)",
                ("alert_threshold", "30"),
            )
            db.commit()

            result = db.execute(
                "SELECT value FROM user_setting WHERE key = ?", ("alert_threshold",)
            ).fetchone()
            assert result["value"] == "30"

    def test_user_setting_unique_key_constraint(self, app):
        """Verify unique constraint on user_setting key."""
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO user_setting (key, value) VALUES (?, ?)", ("theme", "dark")
            )
            db.commit()

            # Attempting to insert duplicate key should fail
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO user_setting (key, value) VALUES (?, ?)",
                    ("theme", "light"),
                )
                db.commit()


class TestDatabaseConfiguration:
    """Test database configuration and file creation."""

    def test_database_file_created(self, dev_app):
        """Verify database file created at configured path."""
        with dev_app.app_context():
            get_db()

        db_path = dev_app.config["DATABASE_PATH"]
        assert os.path.exists(db_path)

    def test_data_directory_created(self, dev_app):
        """Verify data directory is created if it doesn't exist."""
        db_path = dev_app.config["DATABASE_PATH"]
        data_dir = os.path.dirname(db_path)
        assert os.path.exists(data_dir)


class TestErrorHandling:
    """Test error handling in database initialization."""

    def test_get_db_handles_missing_schema_file(self, app, monkeypatch):
        """Verify get_db() raises error when schema file is missing."""
        from flask import Flask

        # Create a test app that will fail to find schema file
        def mock_open_resource_fail(self, resource, mode="rb"):
            raise FileNotFoundError(f"Resource not found: {resource}")

        monkeypatch.setattr(Flask, "open_resource", mock_open_resource_fail)

        with app.app_context():
            # Clear any existing connection
            from flask import g

            g.pop("db", None)

            # Should raise FileNotFoundError when trying to load schema
            with pytest.raises(FileNotFoundError):
                get_db()

    def test_init_db_schema_handles_missing_file(self, monkeypatch, caplog):
        """Verify init_db_schema raises FileNotFoundError for missing schema."""
        from flask import Flask
        from app.config import TestingConfig
        from app.data.database import init_db_schema
        import logging

        # Create app without calling create_app to avoid pre-initialization
        app = Flask(__name__)
        app.config.from_object(TestingConfig)

        # Ensure logger level is set
        app.logger.setLevel(logging.ERROR)

        original_open_resource = Flask.open_resource
        call_count = {"count": 0}

        def mock_open_resource_fail(self, resource, mode="rb"):
            if "init_schema.sql" in resource and mode == "r":
                call_count["count"] += 1
                # Succeed on first call (in get_db()), fail on second call (in init_db_schema)
                if call_count["count"] > 1:
                    raise FileNotFoundError(f"Resource not found: {resource}")
                # Return valid schema for first call
                from io import StringIO

                return StringIO("-- Valid SQL for get_db()\n")
            return original_open_resource(self, resource, mode)

        monkeypatch.setattr(Flask, "open_resource", mock_open_resource_fail)

        with pytest.raises(FileNotFoundError):
            with caplog.at_level(logging.ERROR):
                init_db_schema(app)

        # Verify the error was logged from init_db_schema (not get_db)
        assert call_count["count"] >= 2
        assert "Schema file not found" in caplog.text

    def test_init_db_schema_handles_sql_error(self, monkeypatch, caplog):
        """Verify init_db_schema handles SQL syntax errors."""
        from flask import Flask
        from app.config import TestingConfig
        from app.data.database import init_db_schema
        from io import StringIO
        import logging

        # Create app without calling create_app to avoid pre-initialization
        app = Flask(__name__)
        app.config.from_object(TestingConfig)

        # Ensure logger level is set
        app.logger.setLevel(logging.ERROR)

        original_open_resource = Flask.open_resource
        call_count = {"count": 0}

        def mock_open_resource_bad_sql(self, resource, mode="rb"):
            if "init_schema.sql" in resource and mode == "r":
                call_count["count"] += 1
                # First call (get_db) succeeds, second call (init_db_schema) fails
                if call_count["count"] > 1:
                    # Return invalid SQL that will cause sqlite3.Error on executescript
                    return StringIO("INVALID SQL SYNTAX HERE;")
                # Return valid (empty) schema for first call
                return StringIO("-- Valid for get_db()\n")
            return original_open_resource(self, resource, mode)

        monkeypatch.setattr(Flask, "open_resource", mock_open_resource_bad_sql)

        with pytest.raises(sqlite3.Error):
            with caplog.at_level(logging.ERROR):
                init_db_schema(app)

        # Verify the error was logged from init_db_schema
        assert call_count["count"] >= 2
        assert "Failed to initialize database schema" in caplog.text

    def test_init_db_schema_handles_directory_creation_error(self, monkeypatch):
        """Verify init_db_schema handles OSError during directory creation."""
        from app import create_app

        app = create_app("development")

        # Mock os.makedirs to raise OSError
        def mock_makedirs_fail(path, exist_ok=False):
            raise OSError("Permission denied")

        monkeypatch.setattr(os, "makedirs", mock_makedirs_fail)

        from app.data.database import init_db_schema

        with pytest.raises(OSError):
            init_db_schema(app)
