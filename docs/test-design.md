# Test Design Document

**Project:** deskpulse
**Author:** Boss
**Date:** 2025-12-07
**Version:** 1.0

---

## Overview

This document defines the comprehensive testing strategy for DeskPulse, covering unit tests, integration tests, performance benchmarks, and test infrastructure. The goal is to achieve **70%+ code coverage** on core logic (NFR-M2) while ensuring production readiness on Raspberry Pi 4/5 hardware.

---

## Test Strategy Summary

| Test Type | Coverage Target | Tools | Priority |
|-----------|----------------|-------|----------|
| **Unit Tests** | 70%+ core logic | pytest, pytest-cov | HIGH |
| **Integration Tests** | Critical paths | pytest-flask | HIGH |
| **Performance Tests** | 5+ FPS Pi 4, 10+ FPS Pi 5 | custom benchmarks | HIGH |
| **End-to-End Tests** | User journeys | pytest + systemd | MEDIUM |
| **Security Tests** | OWASP Top 10 | manual + bandit | MEDIUM |

---

## 1. Unit Testing Strategy

### 1.1 Computer Vision Pipeline Tests

**Module:** `app/cv/`

**Testability Requirements:**
- **Controllability:** Mock camera input with pre-recorded frames
- **Observability:** CV thread state accessible via queues
- **Reliability:** Deterministic MediaPipe output for known inputs

**Test Coverage:**

| Component | Test Cases | Mock Strategy |
|-----------|------------|---------------|
| **capture.py** | Camera init, frame read, disconnect handling | Mock cv2.VideoCapture |
| **detection.py** | MediaPipe Pose inference, landmark extraction | Mock mp.solutions.pose.Pose |
| **classification.py** | Good/bad posture binary classification | Pre-labeled test frames |

**Mock Camera Fixture:**

```python
# tests/fixtures/camera.py
import pytest
import numpy as np

@pytest.fixture
def mock_camera_good_posture():
    """Returns 30 frames of good posture (shoulders aligned)"""
    frames = []
    for i in range(30):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Generate synthetic frame with good posture landmarks
        frames.append(frame)
    return frames

@pytest.fixture
def mock_camera_bad_posture():
    """Returns 30 frames of bad posture (hunched shoulders)"""
    frames = []
    for i in range(30):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Generate synthetic frame with bad posture landmarks
        frames.append(frame)
    return frames

@pytest.fixture
def mock_mediapipe():
    """Mock MediaPipe Pose to avoid 2GB model download in CI"""
    class MockPose:
        def process(self, frame):
            # Return mock landmarks based on frame content
            return MockResults()
    return MockPose()
```

**Example Unit Test:**

```python
# tests/test_cv_classification.py
def test_good_posture_classification(mock_camera_good_posture, mock_mediapipe):
    """Verify good posture frames classified correctly"""
    from app.cv.classification import classify_posture

    for frame in mock_camera_good_posture:
        landmarks = mock_mediapipe.process(frame)
        result = classify_posture(landmarks)
        assert result == 'good', "Good posture frame misclassified"

def test_camera_disconnect_graceful_degradation(mock_camera):
    """Verify camera failure triggers graceful degradation, not crash"""
    from app.cv.capture import CameraCapture

    camera = CameraCapture(device=0)
    camera.cap = None  # Simulate disconnect

    result = camera.read_frame()
    assert result is None, "Should return None on disconnect"
    assert camera.state == 'disconnected', "State should update"
```

**Coverage Target:** 80%+ for CV pipeline (critical business logic)

### 1.2 Alert System Tests

**Module:** `app/alerts/`

**Test Coverage:**

| Component | Test Cases |
|-----------|------------|
| **manager.py** | Threshold detection (10 min), notification triggering, pause/resume |

**Example Unit Test:**

```python
# tests/test_alerts.py
def test_alert_triggers_after_10_minutes_bad_posture():
    """Verify alert fires at 10-minute threshold (FR8)"""
    from app.alerts.manager import AlertManager
    import time

    manager = AlertManager(threshold_seconds=600)

    # Simulate 9 minutes 59 seconds of bad posture
    manager.update_posture_state('bad')
    time.sleep(599)
    assert not manager.should_alert(), "Alert should not fire before threshold"

    # Cross threshold
    time.sleep(2)
    assert manager.should_alert(), "Alert should fire after 10 minutes"

def test_pause_stops_alert_tracking():
    """Verify pause control disables alert tracking (FR11)"""
    manager = AlertManager()
    manager.update_posture_state('bad')
    manager.pause()

    time.sleep(600)
    assert not manager.should_alert(), "Paused manager should not alert"
```

**Coverage Target:** 75%+ for alert logic

### 1.3 Database Layer Tests

**Module:** `app/data/`

**Test Configuration:**

```python
# tests/conftest.py
@pytest.fixture
def test_app():
    """Create Flask app with in-memory database for tests"""
    app = create_app('testing')
    with app.app_context():
        init_db(app)
        yield app

@pytest.fixture
def test_db(test_app):
    """Provide clean database for each test"""
    db = get_db()
    yield db
    db.execute("DELETE FROM posture_event")
    db.execute("DELETE FROM user_setting")
    db.commit()
```

**Test Coverage:**

| Component | Test Cases |
|-----------|------------|
| **database.py** | Connection pooling, WAL mode enabled, query performance |
| **models.py** | Posture event CRUD, JSON metadata serialization, pain tracking schema |

**Example Unit Test:**

```python
# tests/test_database.py
def test_wal_mode_enabled(test_db):
    """Verify WAL mode for crash resistance (NFR-R3)"""
    result = test_db.execute("PRAGMA journal_mode").fetchone()
    assert result[0] == 'wal', "WAL mode should be enabled"

def test_pain_tracking_metadata_validation(test_db):
    """Verify pain_level validates 1-10 range"""
    from app.data.models import PostureEvent

    # Valid pain level
    event = PostureEvent(
        timestamp=datetime.now(),
        posture_state='bad',
        metadata={"pain_level": 7}
    )
    event.save(test_db)

    # Invalid pain level should raise
    with pytest.raises(ValueError):
        event = PostureEvent(
            timestamp=datetime.now(),
            posture_state='bad',
            metadata={"pain_level": 11}
        )
        event.save(test_db)
```

**Coverage Target:** 70%+ for data layer

---

## 2. Integration Testing Strategy

### 2.1 End-to-End User Journey Tests

**Test Scenarios:**

| Journey | Test Steps | Success Criteria |
|---------|-----------|------------------|
| **Installation** | Run install.sh → systemd starts → dashboard accessible | Service active, /health returns 200 |
| **Camera Monitoring** | Start app → camera init → posture detected → UI updates | WebSocket receives posture_update events |
| **Alert Workflow** | Bad posture 10 min → notification fires → user pauses → alert stops | libnotify + browser notification triggered |
| **Multi-Device Dashboard** | 10 clients connect → all receive real-time updates | All WebSocket connections receive same events |

**Example Integration Test:**

```python
# tests/test_integration.py
def test_installer_creates_working_system(tmpdir):
    """Verify install.sh produces functional DeskPulse installation"""
    # Run installer in test directory
    result = subprocess.run(
        ['bash', 'scripts/install.sh'],
        cwd=tmpdir,
        env={'INSTALL_DIR': str(tmpdir)},
        capture_output=True
    )

    assert result.returncode == 0, "Installer should succeed"

    # Verify systemd service created
    service_file = tmpdir / 'systemd' / 'deskpulse.service'
    assert service_file.exists(), "Service file should exist"

    # Verify database initialized
    db_file = tmpdir / 'data' / 'deskpulse.db'
    assert db_file.exists(), "Database should be initialized"

@pytest.mark.slow
def test_websocket_multi_client_broadcast(test_app):
    """Verify 10+ simultaneous WebSocket clients receive updates (NFR-SC1)"""
    from flask_socketio import SocketIOTestClient

    clients = []
    for i in range(10):
        client = SocketIOTestClient(test_app, socketio)
        client.connect()
        clients.append(client)

    # Emit posture update from CV thread
    socketio.emit('posture_update', {'state': 'bad', 'timestamp': time.time()})

    # Verify all clients received update
    for client in clients:
        received = client.get_received()
        assert len(received) > 0, f"Client did not receive broadcast"
        assert received[0]['args'][0]['state'] == 'bad'
```

### 2.2 Camera Failure Scenarios

**Test Cases:**

| Scenario | Trigger | Expected Behavior |
|----------|---------|-------------------|
| **Transient disconnect** | Unplug USB 1 sec | 2-layer recovery, reconnect <10 sec (NFR-R4) |
| **Permanent disconnect** | Unplug USB, don't reconnect | Dashboard shows 'disconnected', retries every 10 sec |
| **Permission denied** | Remove video group membership | Clear error log, installer fix documented |
| **Model corruption** | Delete MediaPipe models | Graceful error, not crash loop |

**Example Integration Test:**

```python
# tests/test_camera_failures.py
@pytest.mark.hardware
def test_camera_reconnect_under_10_seconds():
    """Verify camera recovery meets NFR-R4 (<10 sec)"""
    from app.cv.capture import CameraCapture

    camera = CameraCapture(device=0)
    assert camera.state == 'connected'

    # Simulate disconnect
    camera.cap.release()
    camera.cap = None
    camera.state = 'disconnected'

    # Trigger reconnect logic
    start = time.time()
    camera.attempt_reconnect()
    elapsed = time.time() - start

    assert camera.state == 'connected', "Should reconnect"
    assert elapsed < 10, f"Reconnect took {elapsed}s, exceeds 10s target"
```

**Coverage Target:** All critical failure paths tested

---

## 3. Performance Testing Strategy

### 3.1 FPS Benchmarking

**Requirements:**
- **Pi 4:** 5+ FPS sustained (NFR-P1)
- **Pi 5:** 10+ FPS sustained (NFR-P1)
- **Test Duration:** 60 seconds minimum
- **Memory:** <2GB RAM (NFR-P4)

**Benchmark Script:**

```python
# tests/benchmarks/test_fps.py
import time
import psutil

def test_pi4_fps_benchmark():
    """Verify Pi 4 achieves 5+ FPS for 60 seconds"""
    from app.cv.detection import process_frame

    camera = cv2.VideoCapture(0)
    frame_count = 0
    start_time = time.time()

    while time.time() - start_time < 60:
        ret, frame = camera.read()
        if not ret:
            continue

        # Full CV pipeline
        landmarks = process_frame(frame)
        posture = classify_posture(landmarks)
        frame_count += 1

    elapsed = time.time() - start_time
    fps = frame_count / elapsed

    print(f"Pi 4 FPS: {fps:.2f}")
    assert fps >= 5.0, f"FPS {fps:.2f} below 5.0 target"

def test_memory_usage_8_hour_session():
    """Verify no memory leaks during 8-hour operation (NFR-R5)"""
    process = psutil.Process()
    initial_memory = process.memory_info().rss / (1024 ** 3)  # GB

    # Simulate 8 hours (run for 60 sec, extrapolate)
    start = time.time()
    while time.time() - start < 60:
        # CV pipeline iteration
        pass

    final_memory = process.memory_info().rss / (1024 ** 3)
    memory_growth_per_hour = (final_memory - initial_memory) * 8

    assert memory_growth_per_hour < 0.5, f"Memory leak detected: {memory_growth_per_hour}GB/8h"
```

**Hardware Test Matrix:**

| Hardware | Test Environment | Pass Criteria |
|----------|------------------|---------------|
| **Pi 4 (4GB)** | Actual hardware | 5+ FPS, <2GB RAM |
| **Pi 5 (8GB)** | Actual hardware | 10+ FPS, <2GB RAM |
| **x86 Dev** | Mock camera | Tests pass, FPS not measured |

### 3.2 Dashboard Performance

**Requirements:**
- **Load Time:** <2 sec (UX Design)
- **Latency:** <100ms posture change to UI update (NFR-P2)
- **Bundle Size:** Pico CSS <10KB (Architecture)

**Benchmark:**

```python
# tests/benchmarks/test_dashboard_performance.py
def test_dashboard_load_time():
    """Verify dashboard loads in <2 seconds"""
    import requests

    start = time.time()
    response = requests.get('http://localhost:5000/')
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed < 2.0, f"Dashboard loaded in {elapsed}s, exceeds 2s target"

def test_posture_update_latency():
    """Verify <100ms latency from CV thread to WebSocket emit (NFR-P2)"""
    # Measure queue.put() → socketio.emit() latency
    start = time.time()
    cv_queue.put({'state': 'bad', 'timestamp': time.time()})
    # Wait for emit to complete
    time.sleep(0.01)
    latency = time.time() - start

    assert latency < 0.1, f"Latency {latency*1000}ms exceeds 100ms"
```

---

## 4. Test Environments

### 4.1 Development Environment

**Configuration:**
- **Database:** In-memory SQLite (`:memory:`)
- **Camera:** Mock fixture (pre-recorded frames)
- **MediaPipe:** Mocked (no 2GB model download)
- **Logging:** DEBUG level
- **SocketIO:** Test client mode

**Activated via:**

```python
app = create_app('testing')
```

### 4.2 CI/CD Environment (GitHub Actions)

**Configuration:**
- **Runner:** Ubuntu ARM64 (for Pi compatibility)
- **Dependencies:** Install without MediaPipe models
- **Tests:** Unit + integration (no hardware tests)
- **Coverage:** Report to CodeCov

**GitHub Actions Workflow:**

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests with coverage
        run: |
          pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage to CodeCov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=70
```

### 4.3 Staging Environment (Actual Pi Hardware)

**Configuration:**
- **Hardware:** Pi 4 (4GB) + Pi 5 (8GB)
- **Camera:** Logitech C270 USB webcam
- **Database:** SQLite with WAL mode (persistent)
- **systemd:** Service running
- **Tests:** Performance benchmarks, FPS validation

**Test Execution:**

```bash
# On actual Pi hardware
ssh pi@raspberrypi.local
cd ~/deskpulse
source venv/bin/activate

# Run performance tests
pytest tests/benchmarks/ -v --benchmark

# Run hardware-specific tests
pytest tests/test_camera_failures.py -m hardware
```

---

## 5. Test Execution & Reporting

### 5.1 Running Tests Locally

```bash
# All unit tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=app --cov-report=html

# Specific test file
pytest tests/test_cv_classification.py -v

# Skip slow tests
pytest tests/ -v -m "not slow"

# Run only hardware tests (on Pi)
pytest tests/ -v -m hardware
```

### 5.2 Coverage Requirements

**Minimum Coverage Targets (NFR-M2):**

| Module | Coverage Target | Rationale |
|--------|----------------|-----------|
| `app/cv/` | 80% | Core business logic, complex CV pipeline |
| `app/alerts/` | 75% | Critical alert threshold logic |
| `app/data/` | 70% | Database CRUD, simple logic |
| `app/main/routes.py` | 60% | HTTP routes, mostly pass-through |
| `app/system/` | 50% | System utilities, harder to test |
| **Overall** | **70%+** | NFR-M2 requirement |

**Coverage Exclusions:**

```python
# .coveragerc
[run]
omit =
    */tests/*
    */venv/*
    */migrations/*
    */conftest.py
    app/__init__.py  # Factory pattern boilerplate
```

### 5.3 Test Reporting

**pytest Output:**

```
============================= test session starts ==============================
collected 47 items

tests/test_cv_classification.py::test_good_posture_classification PASSED [ 2%]
tests/test_cv_classification.py::test_bad_posture_classification PASSED [ 4%]
tests/test_cv_classification.py::test_camera_disconnect_graceful_degradation PASSED [ 6%]
tests/test_alerts.py::test_alert_triggers_after_10_minutes_bad_posture PASSED [ 8%]
...

---------- coverage: platform linux, python 3.11.5-final-0 -----------
Name                         Stmts   Miss  Cover
------------------------------------------------
app/cv/capture.py               45      8    82%
app/cv/detection.py             67     12    82%
app/cv/classification.py        34      5    85%
app/alerts/manager.py           52     11    79%
app/data/database.py            28      7    75%
------------------------------------------------
TOTAL                          326     58    82%
================================================

====================== 47 passed in 12.34s ======================
```

---

## 6. Test Data & Fixtures

### 6.1 Mock Camera Frames

**Location:** `tests/fixtures/camera_frames/`

```
tests/fixtures/camera_frames/
├── good_posture_001.jpg  # Shoulders aligned
├── good_posture_002.jpg
├── bad_posture_001.jpg   # Hunched shoulders
├── bad_posture_002.jpg
└── no_person_001.jpg     # Empty frame
```

### 6.2 Test Database Fixtures

**Sample Data:**

```python
# tests/fixtures/data.py
@pytest.fixture
def sample_posture_events():
    """7 days of posture data for analytics testing"""
    events = []
    for day in range(7):
        for hour in range(8):
            events.append({
                'timestamp': datetime.now() - timedelta(days=day, hours=hour),
                'posture_state': 'bad' if hour < 4 else 'good',
                'user_present': True,
                'confidence_score': 0.85,
                'metadata': {}
            })
    return events
```

---

## 7. Security Testing

### 7.1 OWASP Top 10 Coverage

| Vulnerability | Test Approach | Status |
|---------------|---------------|--------|
| **SQL Injection** | Parameterized queries enforced | ✅ Mitigated |
| **XSS** | Sanitize pain tracking notes | ⚠️ Manual test needed |
| **CSRF** | CORS restricted to local network | ✅ Fixed (Gap 5) |
| **Authentication** | Optional HTTP basic auth (FR) | ⏳ Week 2 feature |

### 7.2 Security Tooling

```bash
# Static analysis for security issues
bandit -r app/ -ll

# Dependency vulnerability scanning
pip-audit

# CORS configuration validation
curl -H "Origin: http://evil.com" http://localhost:5000/
# Should reject if CORS properly configured
```

---

## 8. Continuous Integration

### 8.1 Pre-Commit Hooks

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest tests/ -v
        language: system
        pass_filenames: false
        always_run: true

      - id: black
        name: black
        entry: black app/ tests/
        language: system
        pass_filenames: false

      - id: flake8
        name: flake8
        entry: flake8 app/ tests/
        language: system
        pass_filenames: false
```

### 8.2 Test Automation Gates

**PR Merge Criteria:**
1. ✅ All unit tests passing
2. ✅ 70%+ code coverage maintained
3. ✅ No flake8 violations
4. ✅ Black formatting applied
5. ✅ Integration tests passing

**Release Criteria:**
1. ✅ All PR merge criteria met
2. ✅ Performance benchmarks passing on Pi 4/5
3. ✅ Hardware tests passing (camera failures, systemd lifecycle)
4. ✅ Security scan clean (bandit, pip-audit)

---

## 9. Test Maintenance

### 9.1 Test Review Schedule

- **Weekly:** Review failing tests, update mocks
- **Sprint End:** Update test coverage report
- **Release:** Full regression test on Pi hardware

### 9.2 Test Debt Tracking

**Known Test Gaps (to address in Epic 6):**

1. ❌ MediaPipe model corruption scenario (low priority)
2. ❌ Accessibility testing (screen reader support)
3. ❌ Multi-camera device selection (medium priority)
4. ❌ Stress testing (1000+ posture events, query performance)

---

## Appendix A: pytest Configuration

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    hardware: marks tests requiring actual Pi hardware
    integration: marks integration tests (vs unit tests)
    benchmark: marks performance benchmarks
addopts =
    -v
    --strict-markers
    --tb=short
    --cov-report=term-missing
```

---

## Appendix B: Coverage Configuration

```ini
# .coveragerc
[run]
source = app
omit =
    */tests/*
    */venv/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
```

---

**Document Status:** ✅ Ready for Implementation
**Next Review:** After Epic 1 completion (Week 1)
