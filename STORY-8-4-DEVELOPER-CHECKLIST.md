# Story 8.4 Developer Implementation Checklist

## Pre-Implementation Checklist

Before starting implementation, verify these baseline items:

- [ ] Read entire story file: `/home/dev/deskpulse/docs/sprint-artifacts/8-4-local-architecture-ipc.md`
- [ ] Review Story 8.1 test patterns: `tests/test_standalone_integration.py`
- [ ] Review Story 8.3 validation report for baseline metrics
- [ ] Understand callback pattern (lines 161-177)
- [ ] Understand event queue design (AC2, lines 193-249)
- [ ] Understand thread-safe state pattern (AC4, lines 344-381)
- [ ] Understand real backend test fixture (lines 464-506)
- [ ] Clarify TrayManager file location (tray_app.py vs tray_manager.py)
- [ ] Clarify event queue instantiation point
- [ ] Understand dual-mode architecture (Pi vs Windows)

## Task Implementation Checklist

### Task 1: Design IPC Architecture (3 hours) - DESIGN PHASE ONLY
**Status:** ✅ COMPLETE IN STORY (No implementation needed)

- [x] 1.1 Design callback registration interface (DOCUMENTED)
- [x] 1.2 Design event queue system (DOCUMENTED)
- [x] 1.3 Map all 12 SocketIO events (DOCUMENTED)
- [x] 1.4 Design thread-safe state management (DOCUMENTED)
- [x] 1.5 Create architecture diagrams (DOCUMENTED)

**Deliverable:** Story file (already complete)

---

### Task 2: Implement Callback Registration System (4 hours)
**Status:** ❌ NOT STARTED
**File:** `app/standalone/backend_thread.py`
**Estimated Lines:** ~200 lines

#### 2.1: Update BackendThread class
- [ ] Add `_callbacks: defaultdict[str, list[Callable]]` attribute
- [ ] Add `_callback_lock: threading.Lock` for thread safety
- [ ] Implement `register_callback(event_type: str, callback: Callable)` method
  - Validates event_type in (alert, correction, status_change, camera_state, error)
  - Adds callback to list
  - Returns success bool
- [ ] Implement `unregister_callback(event_type: str, callback: Callable)` method
  - Removes single callback from list
  - Returns success bool
- [ ] Implement `unregister_all_callbacks()` method
  - Removes ALL callbacks (for shutdown)
  - Called in `BackendThread.stop()` before shutdown
- [ ] Implement `_notify_callbacks(event_type: str, **kwargs)` internal method
  - Copies callback list (snapshot)
  - Iterates and executes each callback
  - Wraps in try-except for exception isolation
  - Logs exceptions with traceback
  - **CRITICAL:** Backend thread MUST NOT crash if callback raises

#### 2.2: Exception Isolation
- [ ] Wrap each callback invocation in try-except
- [ ] Log exceptions with traceback: `logger.exception(f"Callback exception: {e}")`
- [ ] Continue processing remaining callbacks (don't break)
- [ ] Add unit tests for callback exceptions
  - Test: Callback raises Exception - backend continues
  - Test: Multiple callbacks, one fails - all others execute
  - Test: Exception logged correctly
  - Test: Backend thread remains alive

#### 2.3: Support 5 Event Types
- [ ] `alert`: `on_alert(duration: int, timestamp: str, trigger_time: float)`
- [ ] `correction`: `on_correction(previous_duration: int, timestamp: str)`
- [ ] `status_change`: `on_status_change(monitoring_active: bool, threshold_seconds: int)`
- [ ] `camera_state`: `on_camera_state(state: str, timestamp: str)`
- [ ] `error`: `on_error(message: str, error_type: str)`

#### 2.4: Integration with Backend Events
- [ ] CV pipeline alert trigger → `_notify_callbacks('alert', ...)`
- [ ] CV pipeline correction → `_notify_callbacks('correction', ...)`
- [ ] Alert manager pause/resume → `_notify_callbacks('status_change', ...)`
- [ ] Camera state changes → `_notify_callbacks('camera_state', ...)`
- [ ] Error handling → `_notify_callbacks('error', ...)`

#### 2.5: Unit Tests
- [ ] Test callback registration (single)
- [ ] Test callback registration (multiple per event type)
- [ ] Test callback unregistration
- [ ] Test callback unregister_all
- [ ] Test callback invocation with correct parameters
- [ ] Test callback exception isolation (raises, continues)
- [ ] Test thread-safe concurrent registration/invocation

**Testing Framework:** pytest with fixtures from `conftest.py`

---

### Task 3: Implement Priority Event Queue (3 hours)
**Status:** ❌ NOT STARTED
**Files:** `app/standalone/backend_thread.py`, `app/standalone/tray_app.py` (or clarified location)
**Estimated Lines:** ~250 lines

#### 3.1: Create Event Queue in Startup
- [ ] Determine instantiation point (main entry or BackendThread constructor?)
- [ ] Create `queue.PriorityQueue(maxsize=150)` instance
  - Sizing: 10 FPS * 10 sec worst-case latency * 1.5 safety = 150 items
  - Memory: ~30 KB (negligible)
- [ ] Pass to BackendThread constructor
- [ ] Pass to TrayManager constructor

#### 3.2: Define Priority Constants
- [ ] `PRIORITY_CRITICAL = 1` (alerts, errors)
- [ ] `PRIORITY_HIGH = 2` (status changes, camera state)
- [ ] `PRIORITY_NORMAL = 3` (posture corrections)
- [ ] `PRIORITY_LOW = 4` (posture updates, 10 FPS stream)

#### 3.3: Implement Queue Producer in BackendThread
- [ ] Modify `_notify_callbacks()` to also enqueue events
- [ ] Determine priority based on event_type:
  - CRITICAL: alert, error
  - HIGH: status_change, camera_state
  - NORMAL: correction
  - LOW: posture_update
- [ ] Add timestamp to all events: `time.perf_counter()`
  - Used for latency tracking
  - Passed through event tuple
- [ ] Handle queue full strategy:
  - CRITICAL: Block with 1.0 sec timeout (`queue.put(..., timeout=1.0)`)
  - HIGH/NORMAL: Block with 0.5 sec timeout
  - LOW: Latest-wins semantic:
    - Try `put_nowait()` first
    - If queue.Full, remove oldest LOW event before inserting new
    - Track dropped events in metrics
- [ ] Log queue full events: `logger.warning(f"Queue full, dropped {event_type}")`

#### 3.4: Implement Queue Consumer in TrayManager
- [ ] Create consumer thread in TrayManager.__init__()
- [ ] Start consumer as daemon thread in TrayManager.start()
- [ ] Consumer loop:
  ```python
  while self.running:
      try:
          priority, trigger_time, event_type, data = event_queue.get(timeout=0.1)
          self._handle_event(event_type, data, trigger_time)
          queue.task_done()
      except queue.Empty:
          if self.shutdown_event.is_set():
              break
      except Exception as e:
          logger.exception(f"Consumer error: {e}")
  ```
- [ ] Graceful shutdown:
  - Set `self.running = False` and `shutdown_event.set()`
  - Wait for queue drain: `event_queue.join()` (2 sec timeout)
  - Join consumer thread with 5-second timeout
  - Drain remaining events before exit

#### 3.5: Add Queue Metrics Tracking
- [ ] Add metrics attributes:
  - `_events_processed: int = 0`
  - `_events_dropped: int = 0`
  - `_latency_samples: list[float] = []` (keep last 100)
  - `_last_metrics_log: float = time.time()`
- [ ] Increment counters:
  - `_events_processed++` in consumer after `_handle_event()`
  - `_events_dropped++` when queue.Full for LOW priority
  - Add latency sample after delivery: `(delivery_time - trigger_time) * 1000`
- [ ] Log metrics every 60 seconds:
  - Events processed, dropped, drop rate %
  - Latency: min, max, avg, 95th percentile
- [ ] Expose via `backend.get_queue_metrics() -> dict`:
  - Returns: `{events_processed, events_dropped, latency_avg, latency_p95}`

#### 3.6: Integration Tests with Real Queue
- [ ] Test CRITICAL events never dropped (stress test 10 rapid alerts)
- [ ] Test LOW events dropped when queue full (1000 events/sec for 10s)
- [ ] Test priority ordering (CRITICAL processed before LOW)
- [ ] Test queue consumer processes events correctly
- [ ] Test queue shutdown (graceful, no hanging)

---

### Task 4: Replace SocketIO Events with IPC (5 hours)
**Status:** ❌ NOT STARTED
**Files:**
- `app/__init__.py` (Flask factory)
- `app/cv/pipeline.py` (alert emits)
- `requirements-windows.txt` (dependencies)
- `tests/test_standalone_no_socketio.py` (NEW)

#### 4.1: Remove SocketIO from Flask Factory
- [ ] Update `create_app()` in `app/__init__.py`
- [ ] Add conditional import guard (if possible):
  ```python
  if not os.getenv('STANDALONE_MODE'):
      from flask_socketio import SocketIO
  ```
- [ ] Skip `socketio.init_app(app)` when `standalone_mode=True`
  - Already done: Line 99-107 has conditional
- [ ] Skip importing `app.main.events` when `standalone_mode=True`
  - Already done: Line 121 has conditional
- [ ] Add unit test verifying SocketIO not initialized in standalone

#### 4.2: Update CV Pipeline to Use Callbacks
- [ ] Find all `socketio.emit()` calls in `app/cv/pipeline.py`
  - Current: Lines 430, 436, 440 (3 calls total)
- [ ] Replace `socketio.emit('alert_triggered', ...)` with callback:
  - `self.backend_thread._notify_callbacks('alert', duration=..., timestamp=...)`
- [ ] Replace `socketio.emit('posture_corrected', ...)` with callback:
  - `self.backend_thread._notify_callbacks('correction', ...)`
- [ ] Replace `socketio.emit('camera_status', ...)` with callback:
  - `self.backend_thread._notify_callbacks('camera_state', ...)`
- [ ] Keep desktop notifications (libnotify) unchanged
- [ ] Add integration test for callback triggers

#### 4.3: Implement Direct Control Methods in BackendThread
- [ ] `pause_monitoring() -> dict`
  - Calls `alert_manager.pause_monitoring()` with Flask app context
  - Returns: `{success: bool, message: str}`
  - Notifies callbacks: `_notify_callbacks('status_change', monitoring_active=False)`
- [ ] `resume_monitoring() -> dict`
  - Calls `alert_manager.resume_monitoring()` with Flask app context
  - Returns: `{success: bool, message: str}`
  - Notifies callbacks: `_notify_callbacks('status_change', monitoring_active=True)`
- [ ] `get_monitoring_status() -> dict`
  - Thread-safe read (no context needed)
  - Returns: `{monitoring_active, threshold_seconds, cooldown_seconds}`
- [ ] `acknowledge_alert() -> dict`
  - Clears alert state (if needed)
  - Returns: `{success: bool, message: str}`
- [ ] All methods require Flask app context: `with self.flask_app.app_context():`
- [ ] Add thread safety (locks where needed for state mutation)

#### 4.4: Update TrayManager to Use IPC
- [ ] Remove `socketio_client.py` import (if exists)
- [ ] Register callbacks in TrayManager constructor
  ```python
  backend.register_callback('alert', self.on_alert)
  backend.register_callback('correction', self.on_correction)
  # ... etc
  ```
- [ ] Replace SocketIO emits with direct calls:
  - `socketio.emit('pause_monitoring')` → `backend.pause_monitoring()`
  - `socketio.emit('resume_monitoring')` → `backend.resume_monitoring()`
  - `socketio.on('alert_triggered')` → callback registration
- [ ] Update tooltip refresh to use `backend.get_today_stats()` (exists)

#### 4.5: Remove Flask-SocketIO Dependency
- [ ] Remove from `requirements-windows.txt`:
  - `Flask-SocketIO>=5.3.0` (currently line 11-12)
  - `python-socketio>=5.10.0`
  - `python-engineio>=4.8.0`
- [ ] Run `pip uninstall Flask-SocketIO python-socketio python-engineio -y`
- [ ] Run `pip install -r requirements-windows.txt`
- [ ] Verify removal: `pip list | grep socketio` (should return empty)
- [ ] Create `tests/test_standalone_no_socketio.py`:
  - Test: SocketIO not imported in standalone modules
  - Test: `create_app(standalone_mode=True)` doesn't initialize SocketIO
  - Test: No socketio modules in sys.modules after import
- [ ] Test build with PyInstaller (Story 8.6) - verify .exe size reduced ~15 MB
- [ ] Memory validation: <255 MB (vs 265 MB with SocketIO)

---

### Task 5: Implement Thread-Safe Shared State (3 hours)
**Status:** ❌ NOT STARTED
**File:** `app/standalone/backend_thread.py`
**Estimated Lines:** ~150 lines

#### 5.1: Add State Management to BackendThread
- [ ] Add `_state_lock: threading.Lock()` attribute in `__init__`
- [ ] Add state attributes:
  - `_monitoring_active: bool = False`
  - `_threshold_seconds: int = 600`
  - `_cooldown_seconds: int = 180`
  - `_cached_today_stats: dict = {}`
  - `_stats_cache_time: float = 0`

#### 5.2: Implement Thread-Safe State Read Methods
- [ ] `get_monitoring_status() -> dict`
  - Acquire lock with 100ms timeout
  - Return copy of state (not reference)
  - Log warning if lock acquisition fails (potential deadlock)
  - Release lock

#### 5.3: Implement Thread-Safe State Mutation Methods
- [ ] `pause_monitoring() -> dict`
  - Acquire lock
  - Check if already paused
  - Update internal state: `_monitoring_active = False`
  - Release lock BEFORE callback notification (prevent deadlock)
  - Notify callbacks: `_notify_callbacks('status_change', ...)`
  - Return success/error
- [ ] `resume_monitoring() -> dict`
  - Same pattern as pause
  - Set `_monitoring_active = True`

#### 5.4: Add Statistics Caching
- [ ] Cache `get_today_stats()` result for 60 seconds
- [ ] Invalidate cache on monitoring state changes
- [ ] Thread-safe cache access via same lock
- [ ] Log cache hit/miss ratio every 5 minutes

#### 5.5: Stress Test Thread Safety
- [ ] **Concurrent State Access Test:**
  - Spawn 10 threads, each calls `get_monitoring_status()` 1000 times
  - Assert no exceptions, no data corruption
  - Measure lock contention: avg <1ms, max <10ms
- [ ] **Concurrent State Mutation Test:**
  - Spawn 5 threads alternating pause/resume
  - Run 100 operations per thread (500 total)
  - Assert final state consistent
  - Verify all callbacks fired correctly
- [ ] **Callback Registration Stress Test:**
  - 3 threads register/unregister callbacks concurrently
  - 2 threads trigger callbacks concurrently
  - 1000 operations total
  - Assert no crashes
- [ ] **Event Queue Stress Test:**
  - Producer: 1000 events/sec for 60 seconds
  - Consumer: Process concurrently
  - Assert CRITICAL events never dropped
  - Assert no deadlocks
  - Measure throughput: 1000 events/sec
- [ ] **Deadlock Prevention Test:**
  - Hold lock for extended time
  - Assert timeout prevents deadlock
  - Log warning when timeout occurs

---

### Task 6: Measure and Optimize Alert Latency (2 hours)
**Status:** ❌ NOT STARTED
**Files:** `app/cv/pipeline.py`, `app/standalone/backend_thread.py`, notification handler

#### 6.1: Add Latency Instrumentation
- [ ] Record alert trigger time in CV pipeline:
  ```python
  alert_trigger_time = time.perf_counter()
  self.backend._notify_callbacks('alert', ..., trigger_time=alert_trigger_time)
  ```
- [ ] Pass trigger time through callback parameters
- [ ] Calculate latency in notification handler:
  ```python
  delivery_time = time.perf_counter()
  latency_ms = (delivery_time - alert_trigger_time) * 1000
  ```
- [ ] Log latency for every alert: `logger.info(f"Alert latency: {latency_ms:.2f}ms")`

#### 6.2: Identify Latency Bottlenecks
- [ ] Measure callback registration overhead (should be <1ms)
- [ ] Measure queue insertion overhead (should be <5ms)
- [ ] Measure queue retrieval overhead (should be <5ms)
- [ ] Measure notification API call overhead (should be <35ms)
- [ ] Profile with cProfile or line_profiler if needed

#### 6.3: Optimize Critical Path
- [ ] Minimize work in callback invocation
- [ ] Use efficient queue operations (already optimized in stdlib)
- [ ] Pre-allocate event objects if beneficial
- [ ] Batch-process LOW priority events if queue backlogged

#### 6.4: Add Latency Monitoring
- [ ] Track latency percentiles: 50th, 95th, 99th, max
- [ ] Expose via `backend.get_latency_metrics() -> dict`
- [ ] Alert if 95th percentile exceeds 50ms threshold

#### 6.5: Run Performance Validation
- [ ] Single alert latency: 10 samples, 95th <50ms
- [ ] Stress test: 100 alerts in 10 seconds, all <100ms
- [ ] Compare vs SocketIO baseline (~200ms)
- [ ] Document improvement in validation report

---

### Task 7: Integration Tests with Real Backend (4 hours)
**Status:** ❌ NOT STARTED
**File:** `tests/test_local_ipc_integration.py` (NEW)
**Estimated Lines:** ~600 lines

#### 7.1: Create Test File Following Story 8.1 Pattern
- [ ] Import patterns from `test_standalone_integration.py`
- [ ] Use real Flask app (no mocks)
- [ ] Use real database (temp directory)
- [ ] Use real alert manager (no mocks)
- [ ] Use real event queue (queue.PriorityQueue)
- [ ] Mock only cv2.VideoCapture

#### 7.2: Create Real Backend IPC Fixture
```python
@pytest.fixture
def real_backend_with_ipc(temp_appdata):
    db_path = get_database_path()
    event_queue = queue.PriorityQueue(maxsize=20)

    backend = BackendThread(...)
    backend.start()

    yield backend

    backend.stop()
```

#### 7.3: Callback Integration Tests with Real Backend
- [ ] Test alert callback triggered by real alert manager
- [ ] Test correction callback triggered by real CV pipeline
- [ ] Test status change callback on pause/resume
- [ ] Test camera state callback on camera events
- [ ] Test error callback on real errors
- [ ] Verify callbacks execute with correct parameters

#### 7.4: Control Method Integration Tests with Real Backend
- [ ] Test `pause_monitoring()` updates real alert manager
- [ ] Test `resume_monitoring()` restarts real monitoring
- [ ] Test `get_monitoring_status()` returns real state
- [ ] Test `get_today_stats()` returns real database data
- [ ] Test state transitions (pause → resume → pause)

#### 7.5: Event Queue Integration Tests with Real Backend
- [ ] Test priority queue receives real backend events
- [ ] Test CRITICAL events never dropped (real alert triggers)
- [ ] Test event consumer processes real events correctly
- [ ] Test queue shutdown gracefully
- [ ] Test metrics tracking (processed, dropped, latency)

#### 7.6: Code Coverage
- [ ] Run pytest with coverage report: `pytest --cov=app.standalone tests/test_local_ipc_integration.py`
- [ ] Target: 80%+ coverage
- [ ] Add missing test cases for uncovered code
- [ ] Ensure NO mocks of create_app(), AlertManager, Database

---

### Task 8: Windows 10/11 Validation (4 hours actual testing)
**Status:** ❌ NOT STARTED
**Deliverable:** `docs/sprint-artifacts/validation-report-8-4-local-ipc-2026-01-10.md`

#### 8.1: Test on Windows 10 (Build 19045+)
- [ ] Setup test environment
  - Windows 10 PC with built-in webcam
  - Or: USB camera if built-in unavailable
- [ ] Run functionality tests:
  - [ ] Callback registration and invocation
  - [ ] Event queue handling (priority, throughput)
  - [ ] Direct control methods (pause, resume, status)
  - [ ] Thread safety (no crashes under concurrent access)
  - [ ] Alert latency (<50ms)
- [ ] Run 30-minute stability test:
  - [ ] Monitoring active continuously for 30 minutes
  - [ ] Trigger 5+ alerts during test
  - [ ] Use all control methods (pause, resume, status)
  - [ ] Monitor memory usage: sample every 30s
  - [ ] Monitor CPU usage: average over test
  - [ ] Check for crashes or exceptions (zero tolerance)
  - [ ] Verify no memory growth (leak detection)
- [ ] Document results in validation report

#### 8.2: Test on Windows 11 (Build 22621+)
- [ ] Same tests as Windows 10
- [ ] Verify no OS-specific issues
- [ ] Document any differences

#### 8.3: Performance Measurement
- [ ] Memory targets:
  - SocketIO baseline (Story 8.3): 251.8 MB
  - Local IPC target: <255 MB
  - Improvement: -10 MB minimum
- [ ] CPU targets:
  - SocketIO baseline: 35.2%
  - Local IPC target: <35%
  - Improvement: -2% minimum
- [ ] Alert latency:
  - SocketIO baseline: 100-300ms
  - Local IPC target: <50ms (95th percentile)
  - Improvement: -150ms minimum
- [ ] Stress test: 1000 events/sec for 60 seconds

#### 8.4: Create Validation Report
**File:** `docs/sprint-artifacts/validation-report-8-4-local-ipc-2026-01-10.md`

Include:
- [ ] Test results for Windows 10 and Windows 11
- [ ] Latency percentile charts (50th, 95th, 99th)
- [ ] Memory/CPU usage graphs (30-minute test)
- [ ] Performance metrics vs SocketIO baseline
- [ ] Verify targets achieved: <255 MB RAM, <35% CPU, <50ms latency
- [ ] OS-specific behavior notes
- [ ] 0 crashes during 30-minute test
- [ ] All alerts delivered correctly
- [ ] All control methods functional

---

### Task 9: Documentation and Code Cleanup (2 hours)
**Status:** ❌ NOT STARTED

#### 9.1: Update Architecture Documentation
- [ ] Update `docs/architecture.md`
- [ ] Add section: "Standalone Windows IPC"
- [ ] Include architecture diagrams
- [ ] Document callback registration API
- [ ] Document event queue system
- [ ] Document thread safety guarantees

#### 9.2: Update Code Comments
- [ ] Document callback signatures with type hints
- [ ] Document thread safety assumptions (CPython GIL)
- [ ] Document priority levels and event types
- [ ] Add TODO comments for future enhancements

#### 9.3: Remove Dead SocketIO Code (Carefully)
- [ ] Keep SocketIO for Raspberry Pi + web dashboard (multi-client)
- [ ] Only remove from standalone Windows code path
- [ ] Use conditional imports based on `standalone_mode`
- [ ] Document SocketIO still used for Pi edition

#### 9.4: Update User Documentation
- [ ] Document that standalone edition uses local IPC (no network)
- [ ] Update system requirements
- [ ] Add troubleshooting section for IPC issues
- [ ] Update README

---

## Definition of Done Checklist

Before marking story as DONE, verify:

- [ ] All P0 and P1 tasks completed (Tasks 1-8)
- [ ] SocketIO dependency completely removed from standalone build
- [ ] Direct callback mechanism implemented for backend→tray
- [ ] Event queue system implemented with priority handling
- [ ] All 12 SocketIO events replaced with local IPC
- [ ] Alert notifications delivered <50ms latency
- [ ] Pause/resume controls work via direct function calls
- [ ] Monitoring status accessible via shared state
- [ ] All integration tests use real backend (no mocks)
- [ ] Performance improved vs SocketIO (memory -10 MB, CPU -2%)
- [ ] Thread safety validated (stress tested 1000 events/sec)
- [ ] Validated on Windows 10 AND Windows 11
- [ ] 30-minute stability test with 0 crashes
- [ ] No mock data - real Flask app, real database, real alert manager
- [ ] 80%+ code coverage in tests
- [ ] Validation report created with performance comparison

---

## Testing Checklist

### Unit Tests Required
- [ ] Callback registration/unregistration
- [ ] Callback invocation with parameters
- [ ] Callback exception isolation
- [ ] Event queue priority ordering
- [ ] Event queue metrics
- [ ] Thread-safe state access
- [ ] Lock timeout handling
- [ ] Queue overflow handling

### Integration Tests Required (Real Backend)
- [ ] Callback triggered by real backend events
- [ ] Event queue produces/consumes events
- [ ] Direct control methods update real state
- [ ] Thread safety under concurrent access
- [ ] Real Flask app, real database, real alert manager
- [ ] No mocked core services
- [ ] 80%+ code coverage

### Stress Tests Required
- [ ] 1000 events/sec for 60 seconds
- [ ] Concurrent callback registration/invocation
- [ ] Concurrent state mutations
- [ ] Lock contention measurement
- [ ] Queue overflow recovery

### Manual Tests Required
- [ ] Windows 10 (Build 19045+): 30-minute stability
- [ ] Windows 11 (Build 22621+): 30-minute stability
- [ ] 5+ alerts triggered on each OS
- [ ] All control methods tested
- [ ] Memory <255 MB on both OS
- [ ] CPU <35% on both OS
- [ ] Alert latency <50ms
- [ ] Zero crashes

---

## Performance Validation Checklist

### Memory Targets
- [ ] Baseline (SocketIO): 251.8 MB (from Story 8.3)
- [ ] Target (Local IPC): <255 MB
- [ ] Improvement: -10 MB minimum
- [ ] Measured: Every 30 seconds for 30 minutes
- [ ] Documented: In validation report

### CPU Targets
- [ ] Baseline (SocketIO): 35.2%
- [ ] Target (Local IPC): <35%
- [ ] Improvement: -2% minimum
- [ ] Measured: Averaged over 30-minute test
- [ ] Documented: In validation report

### Alert Latency Targets
- [ ] Baseline (SocketIO): 100-300ms
- [ ] Target (Local IPC): <50ms (95th percentile)
- [ ] Improvement: -150ms minimum
- [ ] Measured: For every alert (minimum 10 samples)
- [ ] Documented: Percentile chart (50th, 95th, 99th)

### Event Throughput Targets
- [ ] Stress test: 1000 events/sec for 60 seconds
- [ ] CRITICAL events: Never dropped
- [ ] LOW events: Latest-wins, some dropped if necessary
- [ ] No crashes or deadlocks
- [ ] Documented: In validation report

---

## Git Commit Strategy

### Commits Should Be Organized As:

1. **Task 2 Implementation**
   ```
   Story 8.4: Implement callback registration system

   - Add callback infrastructure to BackendThread
   - Implement register/unregister callback methods
   - Add callback exception isolation
   - Add unit tests (X tests passing)
   ```

2. **Task 5 Implementation**
   ```
   Story 8.4: Implement thread-safe state management

   - Add _state_lock and state attributes
   - Implement pause/resume control methods
   - Add state caching mechanism
   - Add stress tests for concurrency
   ```

3. **Task 3 Implementation**
   ```
   Story 8.4: Implement priority event queue

   - Add queue producer in backend
   - Add queue consumer in tray manager
   - Implement priority handling
   - Add queue metrics tracking
   ```

4. **Task 4 Implementation**
   ```
   Story 8.4: Replace SocketIO with IPC callbacks

   - Replace socketio.emit() with callbacks
   - Implement direct control methods
   - Remove Flask-SocketIO dependency
   - Add verification tests
   ```

5. **Task 6-7 Implementation**
   ```
   Story 8.4: Add latency instrumentation and integration tests

   - Add latency measurement and logging
   - Implement real backend integration tests
   - Verify 80%+ code coverage
   - No mocks of core services
   ```

6. **Task 8 Implementation**
   ```
   Story 8.4: Windows 10/11 validation complete

   - 30-min stability test on Windows 10
   - 30-min stability test on Windows 11
   - Performance vs SocketIO documented
   - Validation report created
   ```

7. **Task 9 Final**
   ```
   Story 8.4: DONE - Local IPC complete

   - Documentation updated
   - Code comments enhanced
   - Rollback plan verified
   - All acceptance criteria met
   ```

---

## Success Criteria

Story 8.4 is **DONE** when:

✅ All 12 SocketIO events replaced with IPC
✅ Callback registration system implemented
✅ Priority event queue system implemented
✅ Thread-safe state management implemented
✅ Direct control methods working
✅ Alert latency <50ms (95th percentile)
✅ Performance improved vs SocketIO (memory -10 MB, CPU -2%)
✅ Thread safety validated (1000 events/sec stress tested)
✅ Windows 10 validation complete (30-min test, 0 crashes)
✅ Windows 11 validation complete (30-min test, 0 crashes)
✅ Integration tests with real backend (80%+ coverage)
✅ No mock data (real Flask app, database, alert manager)
✅ Validation report created with metrics

---

## Resources

- **Story File:** `/home/dev/deskpulse/docs/sprint-artifacts/8-4-local-architecture-ipc.md`
- **Test Pattern:** `/home/dev/deskpulse/tests/test_standalone_integration.py`
- **Backend Thread:** `/home/dev/deskpulse/app/standalone/backend_thread.py`
- **CV Pipeline:** `/home/dev/deskpulse/app/cv/pipeline.py`
- **Flask Factory:** `/home/dev/deskpulse/app/__init__.py`
- **Story 8.3 Report:** `/home/dev/deskpulse/docs/sprint-artifacts/validation-report-8-3-windows-camera-2026-01-10.md`

---

**Generated:** 2026-01-10
**For:** Dev Agent
**Effort:** 30 hours
**Code:** ~1,250 lines
**Tests:** ~600 lines
