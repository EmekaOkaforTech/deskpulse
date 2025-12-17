# Story 2.5: Dashboard UI with Pico CSS

**Epic:** 2 - Real-Time Posture Monitoring
**Story ID:** 2.5
**Story Key:** 2-5-dashboard-ui-with-pico-css
**Status:** Done
**Priority:** High (Critical user-facing component - enables first user interaction with system)

> **✅ Story Context Completed (2025-12-11):** Comprehensive story context created by SM agent using YOLO mode. Includes architecture analysis (Pico CSS design system, Flask routing patterns, semantic HTML), PRD requirements (FR35-FR39), UX Design specification analysis, and previous story learnings from Stories 2.1-2.4. All acceptance criteria validated and ready for dev-story workflow.

---

## User Story

**As a** user accessing DeskPulse,
**I want** a clean, responsive web dashboard that loads quickly on my Pi,
**So that** I can view my posture monitoring without waiting or complex navigation.

---

## Business Context & Value

**Epic Goal:** Users can see their posture being monitored in real-time on web dashboard

**User Value:** This story delivers the first user-facing interface for DeskPulse - the "It works!" moment when users navigate to raspberrypi.local:5000 and see the dashboard. Without this story, all the CV processing (Stories 2.1-2.4) runs invisibly with no way for users to interact with the system. This is the critical bridge between backend processing and user engagement.

**PRD Coverage:**
- FR35: Web dashboard accessible on local network at http://raspberrypi.local:5000
- FR36: mDNS auto-discovery (raspberrypi.local) - DNS resolution provided by Pi OS
- FR37: Live camera feed with pose overlay (placeholder image until Story 2.6 SocketIO)
- FR38: Current posture status display (static placeholder until Story 2.6)
- FR39: Today's running totals (static placeholder until Epic 4)
- NFR-U1: Dashboard loads <2 seconds (Pico CSS enables this)

**User Journey Impact:**
- Sam (Setup User) - "It works!" validation when dashboard appears after installation
- Alex (Developer) - First visual confirmation that CV pipeline is running
- Jordan (Corporate) - Web-based access from any device (laptop, tablet) on local network
- All users - Foundation for real-time monitoring experience (completed in Story 2.6)

**Prerequisites:**
- Story 1.1: Application Factory - MUST be complete (Flask routes registration)
- Story 1.3: Configuration - MUST be complete (PORT configuration)
- Story 1.5: Logging - MUST be complete (deskpulse.api logger)
- Story 2.4: CV Pipeline - MUST be complete (cv_queue provides data source for future stories)

**Downstream Dependencies:**
- Story 2.6: SocketIO Real-Time Updates - consumes dashboard HTML/JS to add live updates
- Story 3.1: Alert Threshold Tracking - adds pause/resume button functionality
- Story 4.3: Dashboard Today's Stats - populates today's summary section with real data
- Story 4.4: 7-Day Historical Data - adds historical data table to dashboard

---

## Acceptance Criteria

### AC1: Base HTML Template with Pico CSS

**Given** I am creating the dashboard layout
**When** I implement the base template
**Then** Pico CSS is loaded from CDN and provides semantic HTML styling

**Implementation:**

```html
<!-- File: app/templates/base.html (NEW FILE) -->
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DeskPulse{% endblock %}</title>

    <!-- Pico CSS v1.5.13 (7-9KB gzipped) - Lightweight semantic HTML framework -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1.5.13/css/pico.min.css">

    <!-- SocketIO client (Story 2.6 will activate) -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>

    <style>
        /* Minimal custom styles - Pico CSS provides most styling */
        .camera-feed {
            max-width: 640px;
            margin: 0 auto;
            border-radius: 8px;
            background-color: var(--card-background-color);
            padding: 1rem;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }

        /* UX Design: Colorblind-safe palette (green/amber, NOT red) */
        .status-good { background-color: #10b981; }     /* Green */
        .status-bad { background-color: #f59e0b; }      /* Amber */
        .status-offline { background-color: #6b7280; }  /* Gray */

        /* Privacy indicator always visible */
        .recording-indicator {
            color: #ef4444;
            font-weight: 600;
        }

        /* Responsive image sizing */
        .camera-feed img {
            width: 100%;
            height: auto;
            display: block;
        }

        /* Placeholder styling */
        .placeholder-text {
            text-align: center;
            padding: 2rem;
            color: var(--muted-color);
        }
    </style>

    {% block extra_head %}{% endblock %}
</head>
<body>
    <main class="container">
        {% block content %}{% endblock %}
    </main>

    <footer class="container" style="text-align: center; margin-top: 2rem; padding: 1rem;">
        <small>
            🔒 Privacy-First Monitoring · 100% Local Processing · No Cloud Uploads
        </small>
    </footer>

    {% block scripts %}{% endblock %}
</body>
</html>
```

**Technical Notes:**
- Pico CSS v1.5.13 provides semantic HTML styling with zero build step
- 7-9KB gzipped bundle size enables <2 second dashboard load (NFR-U1)
- Version pinned for reproducible builds across time
- CSS variables (var(--card-background-color)) support light/dark themes
- SocketIO script pre-loaded for Story 2.6 (inactive until then)
- Container class provides responsive max-width and centering

---

### AC2: Dashboard Page with Live Feed Placeholder

**Given** I navigate to http://raspberrypi.local:5000
**When** the dashboard loads
**Then** I see the camera feed placeholder, posture status, and today's summary

**Implementation:**

```html
<!-- File: app/templates/dashboard.html (NEW FILE) -->
{% extends "base.html" %}

{% block title %}Dashboard - DeskPulse{% endblock %}

{% block content %}
<!-- Header: Project branding and tagline -->
<header>
    <hgroup>
        <h1>DeskPulse</h1>
        <h2>Privacy-First Posture Monitoring</h2>
    </hgroup>
</header>

<!-- Main article: Live camera feed and posture status -->
<article>
    <header>
        <h3>
            <span class="status-indicator status-offline" id="status-dot"></span>
            <span id="status-text">Connecting to camera...</span>
        </h3>
    </header>

    <!-- Live camera feed (placeholder until Story 2.6 SocketIO) -->
    <div class="camera-feed">
        <img id="camera-frame"
             src=""
             alt="Live camera feed with pose overlay"
             style="display: none;">
        <p class="placeholder-text" id="camera-placeholder">
            📹 Waiting for camera feed...<br>
            <small>(Camera feed will appear when CV pipeline is running)</small>
        </p>
    </div>

    <footer>
        <p id="posture-message">Your posture status will appear here when detected.</p>
        <p class="recording-indicator">🔴 Recording: Camera is active</p>
    </footer>
</article>

<!-- Today's stats summary (placeholder until Epic 4) -->
<article>
    <header><h3>Today's Summary</h3></header>
    <div role="group">
        <div>
            <strong>Good Posture:</strong> <span id="good-time">--h --m</span>
        </div>
        <div>
            <strong>Bad Posture:</strong> <span id="bad-time">--h --m</span>
        </div>
        <div>
            <strong>Posture Score:</strong> <span id="posture-score">--%</span>
        </div>
    </div>
    <footer>
        <small>Stats update in real-time as you work (Story 2.6+)</small>
    </footer>
</article>

<!-- Privacy controls (placeholder until Story 3.1) -->
<article>
    <header><h3>Privacy Controls</h3></header>
    <button id="pause-btn" class="secondary" disabled>⏸ Pause Monitoring</button>
    <button id="resume-btn" class="secondary" style="display: none;" disabled>▶️ Resume Monitoring</button>
    <footer>
        <small>
            Privacy controls will be activated in Story 3.1<br>
            Camera indicator shows recording status
        </small>
    </footer>
</article>

<!-- System status (health check indicator) -->
<article>
    <header><h3>System Status</h3></header>
    <p>
        <strong>CV Pipeline:</strong> <span id="cv-status">Checking...</span><br>
        <strong>Last Update:</strong> <span id="last-update">--:--:--</span>
    </p>
</article>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
{% endblock %}
```

**Technical Notes:**
- Semantic HTML structure (header, article, footer) leverages Pico CSS defaults
- Placeholder elements (--h --m, --%) show structure until Epic 4 populates data
- Disabled buttons indicate future functionality (Story 3.1)
- Recording indicator always visible for privacy transparency (UX requirement)
- ID attributes prepared for JavaScript manipulation in Story 2.6

---

### AC3: Flask Route for Dashboard

**Given** the Flask application is running
**When** I navigate to http://raspberrypi.local:5000/
**Then** the dashboard template is rendered

⚠️ **BREAKING CHANGE:** The existing `/` route (app/main/routes.py lines 9-12) returns JSON and must be REMOVED before adding the dashboard route. The existing route was a placeholder from Story 1.1 for installation verification.

✅ **KEEP EXISTING:** The `/health` endpoint already exists at app/main/routes.py lines 15-18 and returns the correct JSON - no changes needed.

**Implementation:**

```python
# File: app/main/routes.py (MODIFY existing file)
# STEP 1: REMOVE existing index() function (lines 9-12)
# STEP 2: ADD new dashboard() function below

from flask import Blueprint, render_template
import logging

logger = logging.getLogger('deskpulse.api')

bp = Blueprint('main', __name__)


@bp.route('/')
def dashboard():
    """
    Main dashboard page (FR35).

    Renders the Pico CSS-based dashboard with live camera feed placeholder,
    posture status, and today's summary. SocketIO updates will activate
    in Story 2.6.

    Returns:
        str: Rendered HTML template
    """
    logger.info("Dashboard accessed")
    return render_template('dashboard.html')


# Keep existing /health endpoint (lines 15-18) - no changes needed
# It already returns: {'status': 'ok', 'service': 'deskpulse'}
```

**Technical Notes:**
- Dashboard route uses GET method (default)
- Health endpoint provides simple uptime check
- Logger uses deskpulse.api component (Story 1.5 logging infrastructure)
- render_template() automatically looks in app/templates/ directory

---

### AC4: Dashboard JavaScript Stub

**Given** Story 2.6 will add SocketIO updates
**When** I create the dashboard JavaScript
**Then** placeholder stubs are ready for real-time update logic

**Implementation:**

```javascript
// File: app/static/js/dashboard.js (NEW FILE)

/**
 * DeskPulse Dashboard JavaScript
 *
 * Story 2.5: Static placeholder stubs
 * Story 2.6: SocketIO real-time updates will activate these functions
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DeskPulse Dashboard loaded');

    // Update CV status to indicate pipeline check
    checkCVPipelineStatus();

    // Set initial timestamp
    updateTimestamp();

    // Story 2.6: SocketIO initialization will go here
    // const socket = io();
    //
    // socket.on('posture_update', function(data) {
    //     updatePostureStatus(data);
    //     updateCameraFeed(data.frame_base64);
    // });
});


/**
 * Check CV pipeline status (Story 2.6 will activate).
 * For now, shows static message.
 */
function checkCVPipelineStatus() {
    const cvStatus = document.getElementById('cv-status');
    cvStatus.textContent = 'Ready (Story 2.6 will activate live updates)';
}


/**
 * Update timestamp display.
 */
function updateTimestamp() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    document.getElementById('last-update').textContent = timeString;
}


/**
 * Update posture status display (Story 2.6 will implement).
 *
 * @param {Object} data - Posture update data from SocketIO
 * @param {string} data.posture_state - 'good', 'bad', or null
 * @param {boolean} data.user_present - User detection status
 */
function updatePostureStatus(data) {
    // Story 2.6: Real implementation
    console.log('Posture update received:', data);
}


/**
 * Update camera feed image (Story 2.6 will implement).
 *
 * @param {string} frameBase64 - Base64-encoded JPEG frame
 */
function updateCameraFeed(frameBase64) {
    // Story 2.6: Real implementation
    console.log('Camera frame received');
}


/**
 * Update today's statistics (Epic 4 will implement).
 *
 * @param {Object} stats - Today's posture statistics
 */
function updateTodayStats(stats) {
    // Epic 4: Real implementation
    console.log('Stats update received:', stats);
}


// Update timestamp every second
setInterval(updateTimestamp, 1000);
```

**Technical Notes:**
- Stub functions document future implementation points
- Console logging helps verify page loads correctly
- setInterval() demonstrates JavaScript is running
- Story 2.6 will uncomment SocketIO code and implement update functions
- JSDoc comments document expected data structures

---

### AC5: Static Assets Directory Structure

**Given** the dashboard needs CSS and JavaScript
**When** I set up the static assets structure
**Then** directories are created following Flask conventions

**Implementation:**

```bash
# Create static assets directory structure
mkdir -p app/static/css
mkdir -p app/static/js
mkdir -p app/static/img

# Create empty CSS file for future custom styles
touch app/static/css/custom.css

# Create dashboard.js (implemented in AC4)
# Created via Write tool in AC4

# Add .gitkeep to ensure directories are tracked
touch app/static/img/.gitkeep
```

**Directory Structure:**

```
app/static/
├── css/
│   └── custom.css (empty - Pico CSS provides all styling for now)
├── js/
│   └── dashboard.js (AC4 - stub functions for Story 2.6)
└── img/
    └── .gitkeep (placeholder for future assets)
```

**Technical Notes:**
- Flask serves static files from app/static/ automatically
- url_for('static', filename='js/dashboard.js') generates correct URL
- Custom CSS file ready for future style overrides
- img/ directory prepared for favicon, logo, etc.

---

### AC6: Unit Tests for Dashboard Route

**Given** the dashboard route is implemented
**When** unit tests run
**Then** route rendering and health check are validated

**Implementation:**

```python
# File: tests/test_dashboard.py (NEW FILE)

import pytest
from flask import url_for


class TestDashboardRoutes:
    """Test suite for dashboard HTTP routes."""

    def test_dashboard_route_exists(self, client):
        """Test dashboard route is accessible."""
        response = client.get('/')

        assert response.status_code == 200
        assert b'DeskPulse' in response.data
        assert b'Privacy-First Posture Monitoring' in response.data

    def test_dashboard_loads_pico_css(self, client):
        """Test Pico CSS v1.5.13 is loaded via CDN."""
        response = client.get('/')

        assert b'@picocss/pico@1.5.13' in response.data
        assert b'pico.min.css' in response.data

    def test_dashboard_has_camera_feed_placeholder(self, client):
        """Test dashboard includes camera feed placeholder."""
        response = client.get('/')

        assert b'camera-feed' in response.data
        assert b'Waiting for camera feed' in response.data

    def test_dashboard_has_posture_status(self, client):
        """Test dashboard includes posture status elements."""
        response = client.get('/')

        assert b'status-indicator' in response.data
        assert b'status-text' in response.data
        assert b'posture-message' in response.data

    def test_dashboard_has_privacy_indicator(self, client):
        """Test privacy recording indicator is always visible."""
        response = client.get('/')

        assert b'recording-indicator' in response.data
        assert b'Recording: Camera is active' in response.data

    def test_dashboard_has_todays_summary(self, client):
        """Test today's summary placeholder exists."""
        response = client.get('/')

        assert b"Today's Summary" in response.data
        assert b'good-time' in response.data
        assert b'bad-time' in response.data
        assert b'posture-score' in response.data

    def test_dashboard_has_privacy_controls(self, client):
        """Test privacy control placeholders exist."""
        response = client.get('/')

        assert b'pause-btn' in response.data
        assert b'resume-btn' in response.data
        assert b'Privacy Controls' in response.data

    def test_dashboard_loads_socketio_script(self, client):
        """Test SocketIO client script is included."""
        response = client.get('/')

        assert b'socket.io' in response.data
        assert b'socket.io.min.js' in response.data

    def test_dashboard_loads_javascript(self, client):
        """Test dashboard.js is loaded."""
        response = client.get('/')

        assert b'dashboard.js' in response.data

    def test_health_endpoint(self, client):
        """Test health check endpoint returns ok."""
        response = client.get('/health')

        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        assert response.json['service'] == 'deskpulse'

    def test_health_endpoint_json_format(self, client):
        """Test health endpoint returns JSON."""
        response = client.get('/health')

        assert response.content_type == 'application/json'
```

**Test Execution:**

```bash
# Run dashboard tests only
PYTHONPATH=/home/dev/deskpulse venv/bin/pytest tests/test_dashboard.py -v

# Run with coverage
PYTHONPATH=/home/dev/deskpulse venv/bin/pytest tests/test_dashboard.py --cov=app.main --cov-report=term-missing
```

**Expected Output:** 11 tests passing

**Technical Notes:**
- Uses Flask test client fixture from conftest.py
- Tests verify HTML structure, not visual rendering
- Content checks use byte strings (b'text') for HTML matching
- Health endpoint tested separately for API functionality
- Coverage target: 100% for app/main/routes.py

---

## Tasks / Subtasks

### Task 1: Create Base HTML Template (AC1)
- [x] Create `app/templates/` directory
- [x] Create `app/templates/base.html` with Pico CSS
- [x] Add semantic HTML structure
- [x] Add custom CSS for camera feed, status indicators
- [x] Add SocketIO script pre-load (inactive until Story 2.6)
- [x] Add footer with privacy messaging

**Acceptance:** AC1 complete

### Task 2: Create Dashboard Page (AC2)
- [x] Create `app/templates/dashboard.html` extending base.html
- [x] Add header with project branding
- [x] Add camera feed placeholder section
- [x] Add posture status indicator
- [x] Add today's summary section with placeholders
- [x] Add privacy controls section (disabled until Story 3.1)
- [x] Add system status section

**Acceptance:** AC2 complete

### Task 3: Implement Flask Routes (AC3)
- [x] Modify `app/main/routes.py` to add dashboard route
- [x] Remove old index() function that returned JSON
- [x] Add new dashboard() function that renders HTML
- [x] Keep health check endpoint unchanged
- [x] Add logging for dashboard access

**Acceptance:** AC3 complete

### Task 4: Create Dashboard JavaScript (AC4)
- [x] Create `app/static/js/` directory
- [x] Create `app/static/js/dashboard.js` with stub functions
- [x] Add DOMContentLoaded event listener
- [x] Add timestamp update function
- [x] Add placeholder functions for Story 2.6 (SocketIO)
- [x] Add JSDoc comments for future implementation

**Acceptance:** AC4 complete

### Task 5: Set Up Static Assets Structure (AC5)
- [x] Create `app/static/css/` directory
- [x] Create `app/static/img/` directory
- [x] Create empty `custom.css` file
- [x] Add .gitkeep to img/ directory
- [x] Verify Flask static file serving works

**Acceptance:** AC5 complete

### Task 6: Unit Tests (AC6)
- [x] Create `tests/test_dashboard.py`
- [x] Implement test_dashboard_route_exists
- [x] Implement test_dashboard_loads_pico_css
- [x] Implement test_dashboard_has_camera_feed_placeholder
- [x] Implement test_dashboard_has_posture_status
- [x] Implement test_dashboard_has_privacy_indicator
- [x] Implement test_dashboard_has_todays_summary
- [x] Implement test_dashboard_has_privacy_controls
- [x] Implement test_dashboard_loads_socketio_script
- [x] Implement test_dashboard_loads_javascript
- [x] Implement test_health_endpoint
- [x] Implement test_health_endpoint_json_format
- [x] Run pytest and verify all 11 tests pass
- [x] Fix test_factory.py health check test to use /health endpoint
- [x] Run flake8 code quality checks

**Acceptance:** AC6 complete - All 11 tests passing, 248 total tests pass

### Task 7: Integration Validation
- [x] **Automated testing complete:**
  - [x] All 248 tests pass (11 new dashboard tests + 237 existing tests)
  - [x] Flake8 code quality checks pass
  - [x] Dashboard route returns HTML with all expected elements
  - [x] Health endpoint returns correct JSON
  - [x] Pico CSS CDN link present in HTML
  - [x] SocketIO script pre-loaded
  - [x] Dashboard JavaScript loaded via template
  - [x] All dashboard sections rendered correctly
- [x] **Code quality validation:**
  - [x] Google-style docstrings added
  - [x] PEP 8 compliance verified
  - [x] No regressions in existing tests
  - [x] Test coverage: 100% for dashboard routes

**Acceptance:** Integration validation complete - All automated tests pass, ready for manual browser testing

---

## Dev Notes

### Architecture Patterns & Constraints

**Dashboard Architecture (architecture.md:275-350):**

- **Pico CSS Design System:** 7-9KB gzipped, zero build step, semantic HTML
- **Flask Blueprint Pattern:** Main blueprint for dashboard routes
- **Template Inheritance:** base.html → dashboard.html
- **Static Assets:** Flask serves from app/static/ automatically
- **CDN Resources:** Pico CSS and SocketIO loaded from CDN (acceptable for local network use)

**UX Design Requirements (ux-design-specification.md):**

- **Emotional Design:** "Quietly Capable" - minimal, unobtrusive, trustworthy
- **Colorblind-Safe Palette:** Green (good), Amber (bad), NOT red
- **Privacy Transparency:** Recording indicator always visible
- **Dashboard Load Time:** <2 seconds (NFR-U1)
- **Responsive Design:** Works on desktop, tablet (mobile not priority)

**Performance Considerations:**

- Pico CSS: 7-9KB gzipped (vs 50-100KB for Bootstrap/Tailwind)
- No JavaScript framework (React, Vue) - vanilla JS keeps it light
- CDN resources cached by browser after first load
- Static HTML template rendered once, updated by SocketIO (Story 2.6)

---

### Network Access Configuration (NFR-S2)

**🔒 SECURITY REQUIREMENT:**

By default, Flask binds to `127.0.0.1` (localhost only) for security. To access the dashboard from other devices on your local network (phones, tablets, other computers):

**Set environment variable:**

```bash
export FLASK_HOST=0.0.0.0  # Binds to all network interfaces
python run.py
```

**Security implications:**

- `127.0.0.1` - Dashboard only accessible from the Pi itself (secure, default)
- `0.0.0.0` - Dashboard accessible from local network (required for FR36 raspberrypi.local access)
- Use OS firewall rules (ufw/nftables) to restrict access to local subnet only
- See Architecture.md NFR-S2 for defense-in-depth strategy

**Testing network access:**

1. Set `FLASK_HOST=0.0.0.0` environment variable
2. Start Flask: `python run.py`
3. From another device on same network: `http://raspberrypi.local:5000`
4. Verify dashboard loads and displays correctly

**mDNS Configuration (FR36):**

No code changes needed. The `raspberrypi.local` hostname is provided by Pi OS Avahi service (built-in mDNS responder). As long as the Pi is on the local network and Flask binds to `0.0.0.0`, clients can access via `http://raspberrypi.local:5000`.

**Troubleshooting:**

- If raspberrypi.local doesn't resolve, use Pi's IP address: `http://192.168.1.x:5000`
- Verify Avahi is running: `systemctl status avahi-daemon`
- Some corporate networks block mDNS - use IP address as fallback

---

### Source Tree Components to Touch

**New Files (Create):**

1. `app/templates/base.html` - Pico CSS base template
2. `app/templates/dashboard.html` - Main dashboard page
3. `app/static/js/dashboard.js` - Dashboard JavaScript stubs
4. `app/static/css/custom.css` - Empty custom styles file
5. `app/static/img/.gitkeep` - Placeholder for image assets
6. `tests/test_dashboard.py` - Dashboard route tests

**Modified Files:**

1. `app/main/routes.py` - Add dashboard and health routes

**No Changes Required:**

- `app/__init__.py` - Blueprint already registered in Story 1.1
- `app/config.py` - No new configuration needed
- `app/main/__init__.py` - Blueprint definition unchanged

---

### Testing Standards Summary

**Unit Test Coverage Target:** 100% for app/main/routes.py

**Test Strategy:**

- Use Flask test client to simulate HTTP requests
- Verify HTML content includes expected elements
- Test health endpoint JSON response
- Verify Pico CSS CDN link is present
- Verify SocketIO script is pre-loaded
- Test semantic HTML structure

**Pytest Command:**

```bash
# Run dashboard tests
PYTHONPATH=/home/dev/deskpulse venv/bin/pytest tests/test_dashboard.py -v

# Run with coverage
PYTHONPATH=/home/dev/deskpulse venv/bin/pytest tests/test_dashboard.py --cov=app.main.routes --cov-report=term-missing

# Run all tests (dashboard + CV)
PYTHONPATH=/home/dev/deskpulse venv/bin/pytest tests/ -v
```

**Manual Browser Testing:**

```bash
# Start Flask development server
python run.py

# Navigate to:
# - http://localhost:5000/ (dashboard)
# - http://localhost:5000/health (health check)

# Verify in browser console:
# - "DeskPulse Dashboard loaded" message appears
# - No JavaScript errors
# - Timestamp updates every second
```

---

### Project Structure Notes

**Module Location:** `app/templates/` and `app/static/` - Flask conventions

**Import Pattern:**

```python
# In routes.py:
from flask import render_template

# Render dashboard:
render_template('dashboard.html')
```

**Static File URL Generation:**

```html
<!-- In templates: -->
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
<link rel="stylesheet" href="{{ url_for('static', filename='css/custom.css') }}">
```

**File Organization:**

- Templates: `app/templates/` (base.html, dashboard.html)
- JavaScript: `app/static/js/` (dashboard.js)
- CSS: `app/static/css/` (custom.css)
- Images: `app/static/img/` (future: favicon, logo)

---

### Library & Framework Requirements

**No New Dependencies:**

Story 2.5 uses only existing dependencies:

- **Flask:** Already installed in Story 1.1 (render_template, Blueprint)
- **Pico CSS:** Loaded via CDN (no local dependency)
- **SocketIO:** Script pre-loaded from CDN (inactive until Story 2.6)

**Dependencies from requirements.txt (unchanged):**

```txt
# Web Framework (Story 1.1)
flask==3.0.0
flask-socketio==5.3.5
python-socketio==5.10.0
```

No version changes or new dependencies for this story.

**CDN Resources:**

```html
<!-- Pico CSS v1.5.13 (version pinned for reproducibility) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1.5.13/css/pico.min.css">

<!-- SocketIO client v4.5.4 -->
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
```

---

### Responsive Design Notes

**Pico CSS Responsive Behavior (MVP):**

- Container class provides responsive max-width and centering
- Camera feed: max-width 640px, scales down on narrow viewports
- Maintains aspect ratio with width: 100%, height: auto
- No custom media queries needed for MVP

**Pico CSS Breakpoints:** Mobile <576px, Tablet 576-768px, Desktop >768px

**Future Growth Phase:** Mobile app (React Native - Story 6.x), Responsive charts (Story 4.5+), Touch controls (Story 5.x)

---

### Previous Work Context

**From Story 2.4 (Multi-Threaded CV Pipeline - COMPLETED):**

- CVPipeline running in dedicated daemon thread
- cv_queue provides posture_state, user_present, frame_base64
- Queue maxsize=1 ensures latest data available
- Flask integration via create_app() in app/__init__.py
- Story 2.6 will consume cv_queue to populate dashboard

**From Story 1.5 (Logging Infrastructure - COMPLETED):**

- Component logger `deskpulse.api` configured
- Development level: DEBUG
- Production level: WARNING
- Dashboard access logged via logger.info()

**From Story 1.3 (Configuration System - COMPLETED):**

- PORT configuration via Config class (default 5000)
- Helper functions: get_ini_int, get_ini_bool
- Pattern: Access via current_app.config

**From Story 1.1 (Application Factory - COMPLETED):**

- create_app() factory pattern
- Blueprint registration: app.register_blueprint(main_bp)
- Main blueprint already created and registered

**Code Quality Standards (Epic 1):**

- PEP 8 compliance, Flake8 passing
- Docstrings in Google style
- Line length: 100 chars max
- Test coverage: 70%+ for routes

---

### UX Design Integration

**Pico CSS Benefits:**

- Semantic HTML: No CSS classes for basic elements (button, header, article)
- Accessibility: Built-in ARIA attributes, keyboard navigation
- Dark Mode: data-theme="light" or "dark" toggle (future)
- Typography: Readable defaults, proper heading hierarchy

**Colorblind-Safe Palette:**

From UX Design Specification:

- Good posture: #10b981 (Green) - universally recognized as positive
- Bad posture: #f59e0b (Amber) - caution without alarm
- Offline/Unknown: #6b7280 (Gray) - neutral state
- **NOT using red:** Red creates anxiety, fails deuteranopia test

**Privacy Transparency:**

- Recording indicator always visible (UX requirement)
- "Privacy-First" messaging in footer
- Pause/resume buttons prominent (disabled until Story 3.1)
- Camera status shows "Camera is active" explicitly

**Progressive Disclosure:**

- Simple default view (live feed + today's stats)
- Advanced settings hidden (future stories)
- No overwhelming information on first load

---

### Git Intelligence Summary

**Recent Work Patterns (Last 5 Commits):**

1. **Story 2.4 drafted** (1966e77) - Multi-threaded CV pipeline complete
2. **Story 2.3 fixes** (65c74c2) - Binary classification code review fixes
3. **Story 2.2 fixes** (fa35314) - MediaPipe pose detection fixes
4. **Story 2.1 fixes** (addadc9) - Camera capture fixes
5. **Epic 1 complete** - Foundation setup validated

**Key Learnings from Git History:**

- Stories follow pattern: Implementation → Code Review → Fixes
- Story documents created in docs/sprint-artifacts/
- Tests added to tests/ directory (separate file per component)
- Blueprint structure established in Epic 1
- Each story builds incrementally on previous work

**Conventions to Follow:**

- Create story document: `docs/sprint-artifacts/2-5-dashboard-ui-with-pico-css.md`
- Create new test file: `tests/test_dashboard.py`
- Update existing routes: `app/main/routes.py`
- Create templates: `app/templates/base.html`, `app/templates/dashboard.html`
- Commit message pattern: "Story 2.5: Dashboard UI with Pico CSS"

---

### References

**Source Documents:**

- PRD: FR35 (Web dashboard), FR36 (mDNS), FR37 (Live feed), FR38 (Posture status), FR39 (Today's totals), NFR-U1 (<2s load)
- Architecture: Flask Application Factory, Blueprint Pattern, Pico CSS Design System, Static Assets Structure
- UX Design Specification: "Quietly Capable" emotion, Colorblind-safe palette, Privacy transparency, Dashboard load time
- Epics: Epic 2 Story 2.5 (Complete acceptance criteria with code examples)
- Story 1.1: Application factory pattern, blueprint registration
- Story 1.3: Configuration system
- Story 1.5: Logging infrastructure
- Story 2.4: CV pipeline, cv_queue data source

**External References:**

- [Pico CSS Documentation](https://picocss.com/) - Semantic HTML framework
- [Flask Templates](https://flask.palletsprojects.com/en/3.0.x/tutorial/templates/) - Jinja2 template documentation
- [Flask Static Files](https://flask.palletsprojects.com/en/3.0.x/tutorial/static/) - Serving static assets
- [SocketIO Client Docs](https://socket.io/docs/v4/client-api/) - JavaScript client API (Story 2.6)
- [Responsive Design Best Practices](https://web.dev/responsive-web-design-basics/) - Viewport meta tag, responsive images

---

## Dev Agent Record

### Context Reference

<!-- Story context created by create-story workflow in YOLO mode -->

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Debug Log References

- **Story context creation date:** 2025-12-11 (SM agent YOLO mode)
- **Previous stories:** 2.1 (Camera) done, 2.2 (Pose) done, 2.3 (Classification) done, 2.4 (Pipeline) done
- **Epic 1 complete:** Foundation setup validated
- **Epic 2 in progress:** Stories 2.1-2.4 complete, 2.5 ready for implementation
- **Architecture analysis:** Pico CSS design system, Flask routing patterns, semantic HTML structure
- **UX Design integration:** "Quietly Capable" emotion, colorblind-safe palette, privacy transparency

### Completion Notes List

**Status:** Done (Code Review Complete)

**Implementation Summary (2025-12-11):**

All acceptance criteria satisfied:
- ✅ AC1: Base HTML template with Pico CSS v1.5.13 (semantic HTML, 7-9KB gzipped)
- ✅ AC2: Dashboard page with camera feed placeholder, posture status, today's summary
- ✅ AC3: Flask route for dashboard (/) rendering HTML template
- ✅ AC4: Dashboard JavaScript stubs ready for Story 2.6 SocketIO integration
- ✅ AC5: Static assets directory structure (css, js, img)
- ✅ AC6: Unit tests - 23 comprehensive tests, all passing, 260 total tests pass

**Code Review (2025-12-11):**

Adversarial code review completed. All 13 findings addressed:
- ✅ HIGH #1: Added null checks to JavaScript DOM manipulation (dashboard.js:36-53)
- ✅ HIGH #2: Expanded test coverage from 11 to 23 tests (security, accessibility, error handling)
- ✅ MEDIUM #3: Added SRI integrity hashes to CDN resources (base.html:9-17)
- ✅ MEDIUM #4: Fixed invalid HTML - removed empty src attribute from img tag (dashboard.html:25-27)
- ✅ MEDIUM #5: Fixed memory leak - added interval cleanup on page unload (dashboard.js:24-29)
- ✅ MEDIUM #6: Added template error handling with graceful degradation (routes.py:23-43)
- ✅ MEDIUM #7: Added negative tests for error scenarios (test_dashboard.py:151-179)
- ✅ MEDIUM #8: Updated File List to include all modified files
- ✅ LOW #9: Moved all inline styles to CSS classes (base.html, dashboard.html)
- ✅ LOW #10: Removed console.log statements from production code
- ✅ LOW #11: Added test fixture validation
- ✅ LOW #12: Added custom.css link to base template (base.html:20)
- ✅ LOW #13: Cleaned up commented code blocks

Final test results: 260 tests passing (23 new dashboard tests, no regressions)

**Key Features Delivered:**

- Pico CSS-based responsive dashboard with semantic HTML structure
- Camera feed placeholder (Story 2.6 will activate with SocketIO)
- Posture status indicator with colorblind-safe palette (green/amber, not red)
- Today's summary section with placeholders (Epic 4 will populate)
- Privacy controls section (disabled until Story 3.1)
- System status display
- Health check endpoint at /health
- Dashboard JavaScript with stub functions for future SocketIO integration

**Testing Coverage:**

- Unit tests: 23 comprehensive dashboard tests (11 baseline + 12 from code review)
  - TestDashboardRoutes: 11 tests (HTML structure, routes)
  - TestDashboardSecurity: 3 tests (SRI integrity, invalid HTML prevention)
  - TestDashboardAccessibility: 4 tests (semantic HTML, ARIA, colorblind-safe)
  - TestDashboardErrorHandling: 3 tests (template errors, 404s, error responses)
  - TestDashboardStaticAssets: 2 tests (CSS loading, static file serving)
- Full regression suite: 260 tests pass (12 new tests, no regressions)
- Code quality: Flake8 passing, PEP 8 compliant, Google-style docstrings
- Test coverage: 100% for app/main/routes.py dashboard and health endpoints

**User Experience Delivered:**

- Dashboard accessible at http://raspberrypi.local:5000/ (FR35, FR36)
- Clean, minimal design with Pico CSS semantic styling
- Privacy indicator always visible (transparency requirement)
- Responsive layout works on desktop and tablet
- Foundation ready for Story 2.6 real-time updates

**Technical Implementation:**

- Removed old index() route that returned JSON (breaking change documented in AC3)
- Updated test_factory.py to use /health endpoint instead of /
- Dashboard route logs access via deskpulse.api logger
- Templates use Jinja2 inheritance (base.html → dashboard.html)
- Static files served from app/static/ (Flask conventions)
- SocketIO client script pre-loaded from CDN (inactive until Story 2.6)

### File List

**New Files:**
- app/templates/base.html
- app/templates/dashboard.html
- app/static/js/dashboard.js
- app/static/css/custom.css (empty)
- app/static/img/.gitkeep
- tests/test_dashboard.py

**Modified Files:**
- app/main/routes.py (replaced index() with dashboard(), added error handling)
- app/templates/base.html (added SRI integrity, custom.css link, CSS classes)
- app/templates/dashboard.html (fixed invalid HTML, moved inline styles to classes)
- app/static/js/dashboard.js (added null checks, memory leak fix, cleaned up code)
- tests/test_dashboard.py (23 comprehensive tests covering security, accessibility, errors)
- tests/test_factory.py (updated health check test to use /health endpoint)
- docs/sprint-artifacts/2-5-dashboard-ui-with-pico-css.md (this file)
- docs/sprint-artifacts/sprint-status.yaml (story status tracking)

