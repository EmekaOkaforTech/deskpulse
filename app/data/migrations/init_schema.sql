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
