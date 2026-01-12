# Fix CVPipeline for Windows Camera Support

**Issue:** CVPipeline doesn't properly handle external Windows camera

**Required Changes:** Edit `app/cv/pipeline.py` on Windows machine

---

## Change 1: Update __init__ signature (Line 61)

**Find:**
```python
def __init__(self, fps_target: int = 10, app=None):
```

**Replace with:**
```python
def __init__(self, fps_target: int = 10, app=None, camera=None):
```

---

## Change 2: Add camera parameter handling (After line 79)

**Find:**
```python
self.app = app  # Store Flask app for background thread app context
self.camera = None
```

**Replace with:**
```python
self.app = app  # Store Flask app for background thread app context
self.camera = camera  # Story 8.1: Use external camera if provided
self.external_camera = camera is not None  # Track if using external camera
```

---

## Change 3: Fix camera initialization in start() (Around line 132)

**Find:**
```python
self.camera = CameraCapture()
```

**Replace with:**
```python
# Only create CameraCapture if not using external camera (Story 8.1)
if not self.external_camera:
    self.camera = CameraCapture()
```

---

## Change 4: Handle external camera open() (Around line 143)

**Find:**
```python
# Initialize camera (Story 2.1 pattern)
if not self.camera.initialize():
    logger.error(
        "Failed to initialize camera"
    )
    self._emit_camera_status('disconnected')
    # Don't fail startup - camera may connect later
    # Thread will retry connection
else:
    # Enterprise: Emit connected status on successful startup
    self.camera_state = 'connected'
    self._emit_camera_status('connected')
```

**Replace with:**
```python
# Initialize camera (Story 2.1 pattern)
if not self.external_camera:
    # Internal CameraCapture - use initialize()
    if not self.camera.initialize():
        logger.error(
            "Failed to initialize camera"
        )
        self._emit_camera_status('disconnected')
        # Don't fail startup - camera may connect later
        # Thread will retry connection
    else:
        # Enterprise: Emit connected status on successful startup
        self.camera_state = 'connected'
        self._emit_camera_status('connected')
else:
    # Story 8.1: External camera (WindowsCamera) - use open()
    logger.info("Using external camera (Story 8.1)")
    if not self.camera.open():
        logger.error("Failed to open external camera")
        self._emit_camera_status('disconnected')
        # Don't fail startup - will retry in processing loop
    else:
        self.camera_state = 'connected'
        self._emit_camera_status('connected')
```

---

## Change 5: Handle camera.read() vs camera.read_frame() (Around line 300)

**Find:**
```python
# Attempt frame capture
ret, frame = self.camera.read_frame()
```

**Replace with:**
```python
# Attempt frame capture
# Story 8.1: Handle both CameraCapture and WindowsCamera interfaces
if self.external_camera:
    ret, frame = self.camera.read()
else:
    ret, frame = self.camera.read_frame()
```

---

## Change 6: Handle retry logic (Around line 324)

**Find:**
```python
# Release and reinitialize camera
self.camera.release()
time.sleep(QUICK_RETRY_DELAY)

if self.camera.initialize():
    ret, frame = self.camera.read_frame()
    if ret:
        self.camera_state = 'connected'
        logger.info(
            f"Camera reconnected after {attempt} "
            f"quick retries"
        )
        self._emit_camera_status('connected')
        reconnected = True
        break
```

**Replace with:**
```python
# Release and reinitialize camera
self.camera.release()
time.sleep(QUICK_RETRY_DELAY)

# Story 8.1: Handle both camera interfaces
camera_init_ok = (
    self.camera.open() if self.external_camera
    else self.camera.initialize()
)

if camera_init_ok:
    # Try to read a frame
    if self.external_camera:
        ret, frame = self.camera.read()
    else:
        ret, frame = self.camera.read_frame()

    if ret:
        self.camera_state = 'connected'
        logger.info(
            f"Camera reconnected after {attempt} "
            f"quick retries"
        )
        self._emit_camera_status('connected')
        reconnected = True
        break
```

---

## After Making Changes

Save the file and run:

```powershell
$env:PYTHONPATH = "C:\deskpulse-build\deskpulse_installer"
python windows_perf_test.py
```

This time you should see:
- Camera opens successfully
- CV pipeline starts without errors
- Memory climbs above 100MB (actual processing)
- CPU shows activity (pose detection working)

---

**Created:** 2026-01-08
**Purpose:** Manual fix for CVPipeline Windows camera support
