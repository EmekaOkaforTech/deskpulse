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

-- Achievement system tables (Phase 2)
-- Stores achievement type definitions
CREATE TABLE IF NOT EXISTS achievement_type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,           -- 'first_perfect_hour', 'week_warrior', etc.
    name TEXT NOT NULL,                   -- Display name: "First Perfect Hour"
    description TEXT NOT NULL,            -- "Maintain good posture for 60 consecutive minutes"
    category TEXT NOT NULL,               -- 'daily', 'weekly', 'milestone'
    icon TEXT DEFAULT '🏆',               -- Emoji or icon identifier
    points INTEGER DEFAULT 10,            -- Gamification points value
    tier TEXT DEFAULT 'bronze',           -- 'bronze', 'silver', 'gold', 'platinum'
    is_active BOOLEAN DEFAULT 1,          -- Can be disabled without deletion
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_achievement_type_category ON achievement_type(category);
CREATE INDEX IF NOT EXISTS idx_achievement_type_code ON achievement_type(code);

-- Stores earned achievements per user session/device
CREATE TABLE IF NOT EXISTS achievement_earned (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_type_id INTEGER NOT NULL,
    earned_at DATETIME NOT NULL,
    metadata JSON,                        -- Context: {'score': 85, 'streak_days': 7}
    notified BOOLEAN DEFAULT 0,           -- Track if user was notified
    FOREIGN KEY (achievement_type_id) REFERENCES achievement_type(id)
);

CREATE INDEX IF NOT EXISTS idx_achievement_earned_type ON achievement_earned(achievement_type_id);
CREATE INDEX IF NOT EXISTS idx_achievement_earned_date ON achievement_earned(earned_at);

-- Daily tracking for achievement progress (prevents duplicate daily achievements)
CREATE TABLE IF NOT EXISTS achievement_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_code TEXT NOT NULL,       -- References achievement_type.code
    tracking_date DATE NOT NULL,          -- Date being tracked
    progress_value REAL DEFAULT 0,        -- Current progress (e.g., minutes, percentage)
    target_value REAL NOT NULL,           -- Target to earn achievement
    completed BOOLEAN DEFAULT 0,          -- Whether achievement was earned
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(achievement_code, tracking_date)
);

CREATE INDEX IF NOT EXISTS idx_achievement_progress_date ON achievement_progress(tracking_date);

-- Seed default achievement types (Open Source Edition - 9 achievements)
-- NOTE: Daily achievements require 1+ hour monitoring; Getting Started requires 30+ min
-- Premium achievements available in closed-source edition
INSERT OR IGNORE INTO achievement_type (code, name, description, category, icon, points, tier) VALUES
    -- Daily Achievements (require 1+ hour of monitoring to prevent false awards)
    ('first_perfect_hour', 'First Perfect Hour', 'Accumulate 60 minutes of good posture in one day', 'daily', '⏱️', 10, 'bronze'),
    ('posture_champion', 'Posture Champion', 'Achieve 80%+ posture score (requires 1hr+ monitoring)', 'daily', '🏆', 15, 'silver'),
    ('early_bird', 'Early Bird', '10+ minutes good posture before 8 AM (requires 1hr+ monitoring)', 'daily', '🌅', 10, 'bronze'),
    ('night_owl', 'Night Owl', '10+ minutes good posture after 8 PM (requires 1hr+ monitoring)', 'daily', '🦉', 10, 'bronze'),

    -- Weekly Achievements (checked on Sundays, require 7 days with 30+ min monitoring each)
    ('week_warrior', 'Week Warrior', 'Achieve 70%+ average score for 7 consecutive days', 'weekly', '⚔️', 50, 'gold'),
    ('perfect_week', 'Perfect Week', 'Achieve 80%+ score on 5 or more days in a week', 'weekly', '🌟', 40, 'gold'),

    -- Milestone Achievements (one-time awards)
    ('getting_started', 'Getting Started', 'Complete 30+ minutes of posture monitoring', 'milestone', '🚀', 10, 'bronze'),
    ('habit_builder', 'Habit Builder', 'Track posture for 7 consecutive days (30+ min each)', 'milestone', '🔨', 25, 'silver'),
    ('transformation', 'Transformation', 'Achieve a 90%+ daily score for the first time (requires 1hr+ monitoring)', 'milestone', '🦋', 50, 'gold');
