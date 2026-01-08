# MediaPipe Tasks API Migration Guide (Story 8.2)

**For Contributors:** This guide explains the MediaPipe Tasks API migration completed in Story 8.2.

**Migration Date:** 2026-01-08
**Story:** 8.2 - Migrate to MediaPipe Tasks API (0.10.31/0.10.18)
**Status:** COMPLETE - Production Ready

---

## Table of Contents

1. [What Changed](#what-changed)
2. [Why We Migrated](#why-we-migrated)
3. [API Comparison](#api-comparison)
4. [Key Differences](#key-differences)
5. [Code Examples](#code-examples)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [References](#references)

---

## What Changed

### Summary

DeskPulse migrated from MediaPipe **Solutions API** (deprecated) to **Tasks API** (official replacement).

**Before (v1.x - MediaPipe 0.10.21):**
- Used `mediapipe.python.solutions.pose.Pose()`
- Embedded models in package (~230MB total)
- Protobuf landmark structure
- Single version for all platforms

**After (v2.0+ - MediaPipe 0.10.31/0.10.18):**
- Uses `mediapipe.tasks.python.vision.PoseLandmarker`
- External model files (9MB `.task` files)
- List landmark structure
- Platform-specific versions (x64 vs ARM64)

### Files Changed

- `app/cv/detection.py` - Core pose detection (Tasks API integration)
- `app/cv/classification.py` - Posture classification (landmark access updated)
- `app/config.py` - Configuration management (backward compatibility added)
- `requirements.txt` - Dependency versions (platform-specific)
- `tests/test_cv.py` - Unit tests (mocks updated)
- `tests/integration/test_cv_pipeline_tasks_api.py` - Integration tests (NEW)

---

## Why We Migrated

### Official Deprecation

Google deprecated Solutions API in March 2023:

> "The MediaPipe Solutions API is deprecated. Please migrate to Tasks API for continued support and updates."
> - Source: [MediaPipe Documentation](https://developers.google.com/mediapipe/solutions)

### Benefits

1. **Future-Proofing:** Tasks API is actively maintained (Solutions API will be removed)
2. **Package Size:** 80MB reduction (jax/jaxlib/matplotlib dependencies removed)
3. **Modularity:** External model files enable easier model swapping
4. **Performance:** Same BlazePose model, no regression
5. **API Stability:** Official Google support and documentation

### Business Impact

- **Installer Size:** Reduced by ~80MB (better user experience)
- **Deployment Speed:** Faster pip installs, smaller Docker images
- **Maintenance:** Future Google updates will support Tasks API only

---

## API Comparison

### Import Statements

**Before (Solutions API):**
```python
import mediapipe as mp

# Solutions API imports
pose = mp.solutions.pose
drawing = mp.solutions.drawing_utils
```

**After (Tasks API):**
```python
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Keep solutions for drawing and enums
drawing = mp.solutions.drawing_utils
pose_enums = mp.solutions.pose  # For PoseLandmark enum constants
```

### Initialization

**Before (Solutions API):**
```python
self.pose = mp.solutions.pose.Pose(
    static_image_mode=False,
    model_complexity=1,  # 0=lite, 1=full, 2=heavy
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
```

**After (Tasks API):**
```python
# Create options
options = vision.PoseLandmarkerOptions(
    base_options=python.BaseOptions(
        model_asset_path="app/cv/models/pose_landmarker_full.task"
    ),
    running_mode=vision.RunningMode.VIDEO,  # VIDEO mode for streams
    num_poses=1,  # Detect single person
    min_pose_detection_confidence=0.5,
    min_tracking_confidence=0.5,
    output_segmentation_masks=False  # Disable to save CPU
)

# Create landmarker instance
self.landmarker = vision.PoseLandmarker.create_from_options(options)
```

### Detection

**Before (Solutions API):**
```python
# Process frame
results = self.pose.process(rgb_frame)

# Check if pose detected
if results.pose_landmarks:
    landmarks = results.pose_landmarks
    # landmarks is a protobuf NormalizedLandmarkList
```

**After (Tasks API):**
```python
# Create MediaPipe Image object
mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

# Generate timestamp (VIDEO mode requirement)
timestamp_ms = int(frame_counter * 100)  # 100ms per frame @ 10 FPS
frame_counter += 1

# Detect pose
results = self.landmarker.detect_for_video(mp_image, timestamp_ms)

# Check if pose detected
if results.pose_landmarks and len(results.pose_landmarks) > 0:
    landmarks = results.pose_landmarks[0]  # List of NormalizedLandmark objects
    # landmarks is a list (not protobuf)
```

### Landmark Access

**Before (Solutions API):**
```python
from mediapipe.python.solutions import pose as mp_pose

# Protobuf structure
nose = results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE]
left_shoulder = results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER]

# Access coordinates
x = nose.x
y = nose.y
visibility = nose.visibility
```

**After (Tasks API):**
```python
from mediapipe import solutions as mp_solutions

# List structure (requires .value to get integer index)
nose = landmarks[mp_solutions.pose.PoseLandmark.NOSE.value]
left_shoulder = landmarks[mp_solutions.pose.PoseLandmark.LEFT_SHOULDER.value]

# Access coordinates (same as before)
x = nose.x
y = nose.y
visibility = nose.visibility
```

### Drawing Landmarks

**Before (Solutions API):**
```python
# Direct drawing (protobuf format)
mp.solutions.drawing_utils.draw_landmarks(
    frame,
    results.pose_landmarks,  # Protobuf NormalizedLandmarkList
    mp.solutions.pose.POSE_CONNECTIONS
)
```

**After (Tasks API):**
```python
from mediapipe.framework.formats import landmark_pb2

# Convert list to protobuf for drawing utilities
landmark_proto = landmark_pb2.NormalizedLandmarkList()
for lm in landmarks:
    landmark_proto.landmark.add(
        x=lm.x,
        y=lm.y,
        z=lm.z,
        visibility=lm.visibility,
        presence=lm.presence
    )

# Draw with proto format
mp.solutions.drawing_utils.draw_landmarks(
    frame,
    landmark_proto,
    mp.solutions.pose.POSE_CONNECTIONS
)
```

### Cleanup

**Before (Solutions API):**
```python
self.pose.close()  # Release MediaPipe resources
```

**After (Tasks API):**
```python
self.landmarker.close()  # Release MediaPipe resources
```

---

## Key Differences

### 1. Landmark Structure

| Aspect | Solutions API | Tasks API |
|--------|--------------|-----------|
| **Data Type** | Protobuf `NormalizedLandmarkList` | Python `list` of `NormalizedLandmark` |
| **Access Pattern** | `landmarks.landmark[enum]` | `landmarks[enum.value]` |
| **Index Type** | Enum object | Integer (enum.value) |
| **Example** | `landmarks.landmark[PoseLandmark.NOSE]` | `landmarks[PoseLandmark.NOSE.value]` |

### 2. Detection Method

| Aspect | Solutions API | Tasks API |
|--------|--------------|-----------|
| **Method** | `process(frame)` | `detect_for_video(mp_image, timestamp_ms)` |
| **Input** | NumPy array (RGB) | `mp.Image` object |
| **Timestamp** | Not required | Required for VIDEO mode |
| **Running Mode** | Static image mode flag | Explicit `RunningMode` enum |

### 3. Model Files

| Aspect | Solutions API | Tasks API |
|--------|--------------|-----------|
| **Location** | Embedded in package | External `.task` files |
| **Size** | ~230MB (total package) | ~9MB (model file only) |
| **Path** | N/A (bundled) | `app/cv/models/*.task` |
| **Download** | Automatic (pip install) | Manual or installer script |

### 4. Configuration

| Aspect | Solutions API | Tasks API |
|--------|--------------|-----------|
| **Config Key** | `model_complexity = 0/1/2` | `model_file = *.task` |
| **Values** | Integer (0=lite, 1=full, 2=heavy) | Filename (string) |
| **Backward Compat** | N/A | Auto-migrates old configs |

---

## Code Examples

### Example 1: Complete PoseDetector Class

See `app/cv/detection.py` (lines 1-301) for production implementation.

**Key Methods:**
- `__init__(app=None)` - Initialize with Tasks API
- `_resolve_model_path(model_file)` - Resolve model file path
- `detect_landmarks(frame)` - Detect pose in frame (Tasks API)
- `draw_landmarks(frame, landmarks, color)` - Draw skeleton overlay
- `close()` - Release resources

### Example 2: Posture Classification

See `app/cv/classification.py` (lines 1-212) for production implementation.

**Landmark Access Pattern:**
```python
from mediapipe import solutions

class PostureClassifier:
    def __init__(self, app=None):
        self.mp_pose = solutions.pose

    def classify_posture(self, landmarks):
        """Classify posture from Tasks API landmarks (list format)."""
        if landmarks is None:
            return None

        # Access landmarks using enum.value (Tasks API)
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

        # Calculation logic unchanged
        # ...
```

### Example 3: Integration Test (Real Backend)

See `tests/integration/test_cv_pipeline_tasks_api.py` for complete test suite.

**Key Test:**
```python
def test_classification_accepts_list_landmarks():
    """Verify PostureClassifier accepts Tasks API list format."""
    from app.cv.classification import PostureClassifier

    # Create mock landmarks as list (Tasks API format)
    class MockLandmark:
        def __init__(self, x, y, z):
            self.x = x
            self.y = y
            self.z = z
            self.visibility = 0.95
            self.presence = 0.98

    # 33 landmarks (MediaPipe Pose standard)
    landmarks = [MockLandmark(0.5, 0.5, 0.0) for _ in range(33)]

    # Set key landmarks
    from mediapipe import solutions
    mp_pose = solutions.pose
    landmarks[mp_pose.PoseLandmark.NOSE.value] = MockLandmark(0.5, 0.2, -0.1)
    landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value] = MockLandmark(0.4, 0.3, -0.1)

    # Test classification
    classifier = PostureClassifier()
    posture = classifier.classify_posture(landmarks)

    assert posture in ['good', 'bad']  # Should not crash
```

---

## Testing

### Run Tests

**Unit Tests (Mocks):**
```bash
cd /home/dev/deskpulse
source venv/bin/activate
pytest tests/test_cv.py::TestPoseDetector -v
```

**Expected:** 7/7 tests passing ✅

**Integration Tests (Real Backend):**
```bash
PYTHONPATH=/home/dev/deskpulse pytest tests/integration/test_cv_pipeline_tasks_api.py -v
```

**Expected:** 5/5 tests passing ✅
- Model file path resolution
- PoseDetector initialization with real model
- Landmark detection returns list format
- Classification accepts list landmarks
- End-to-end pipeline validation

### Manual Testing

**Test Pose Detection:**
```bash
cd /home/dev/deskpulse
source venv/bin/activate

# Run backend
python wsgi.py

# Open browser: http://localhost:5000
# Position yourself in front of webcam
# Verify skeleton overlay appears (green = good posture, amber = bad)
```

---

## Troubleshooting

### Issue #1: Model File Not Found

**Error:**
```
FileNotFoundError: MediaPipe model file not found: /path/to/pose_landmarker_full.task
```

**Solution:**
```bash
mkdir -p app/cv/models
cd app/cv/models
curl -L -o pose_landmarker_full.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
```

### Issue #2: AttributeError on Landmark Access

**Error:**
```
AttributeError: 'list' object has no attribute 'landmark'
```

**Cause:** Using Solutions API access pattern on Tasks API landmarks.

**Solution:**
```python
# WRONG (Solutions API pattern):
nose = landmarks.landmark[PoseLandmark.NOSE]

# CORRECT (Tasks API pattern):
nose = landmarks[PoseLandmark.NOSE.value]
```

### Issue #3: TypeError - list indices must be integers

**Error:**
```
TypeError: list indices must be integers, not PoseLandmark
```

**Cause:** Missing `.value` on enum.

**Solution:**
```python
# WRONG:
nose = landmarks[PoseLandmark.NOSE]  # Enum object, not integer

# CORRECT:
nose = landmarks[PoseLandmark.NOSE.value]  # .value converts to integer (0)
```

### Issue #4: ImportError - cannot import PoseLandmarker

**Error:**
```
ImportError: cannot import name 'PoseLandmarker' from 'mediapipe.tasks.python.vision'
```

**Cause:** MediaPipe version too old.

**Solution:**
```bash
# Raspberry Pi (ARM64):
pip install mediapipe==0.10.18 --upgrade --force-reinstall

# Windows/Linux (x86_64):
pip install mediapipe==0.10.31 --upgrade --force-reinstall
```

### Issue #5: Performance Regression

**Symptom:** Slower pose detection after migration.

**Diagnosis:**
1. Check model file: Should be `pose_landmarker_full.task` (not lite/heavy)
2. Verify CPU not thermal throttling: `vcgencmd measure_temp` (Pi)
3. Close background apps consuming CPU
4. Check FPS target: Should be 10 FPS (not higher)

**Expected Performance (same as pre-migration):**
- Memory: ~240-260 MB
- CPU: ~30-40% (Pi 4B)
- FPS: 10 (stable)

---

## References

### MediaPipe Documentation

- **Tasks API Guide:** https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python
- **Migration Overview:** https://developers.google.com/mediapipe/solutions/tasks
- **Pose Landmarker Source:** https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/python/vision/pose_landmarker.py
- **Model Files:** https://storage.googleapis.com/mediapipe-models/pose_landmarker/

### DeskPulse Documentation

- **Story 8.2 (Full Spec):** `docs/sprint-artifacts/8-2-mediapipe-tasks-api-migration.md`
- **Baseline Documentation:** `docs/baselines/migration-acceptance.md`
- **Architecture:** `docs/architecture.md` (External Integrations section)
- **Code Review Report:** `docs/sprint-artifacts/validation-report-8-2-mediapipe-migration-2026-01-08.md`

### Testing

- **Integration Tests:** `tests/integration/test_cv_pipeline_tasks_api.py`
- **Unit Tests:** `tests/test_cv.py` (PoseDetector section)

---

## Summary for Contributors

**If you're working on pose detection code:**

1. ✅ Use `mediapipe.tasks.python.vision.PoseLandmarker` (NOT `mp.solutions.pose.Pose`)
2. ✅ Access landmarks with `.value`: `landmarks[enum.value]` (NOT `landmarks.landmark[enum]`)
3. ✅ Use `detect_for_video()` with timestamp (NOT `process()`)
4. ✅ Convert to proto for drawing: `landmark_pb2.NormalizedLandmarkList()`
5. ✅ Test with real backend: Run integration tests (no mocks)

**If you're updating dependencies:**

1. ✅ Use platform-specific versions in `requirements.txt`
2. ✅ x86_64: `mediapipe==0.10.31`
3. ✅ aarch64: `mediapipe==0.10.18`

**If you're modifying tests:**

1. ✅ Mock `vision.PoseLandmarker` (NOT `mp.solutions.pose.Pose`)
2. ✅ Mock `detect_for_video()` (NOT `process()`)
3. ✅ Return list format (NOT protobuf)

---

**Questions?** See Story 8.2 artifacts or contact maintainers.

**Status:** ✅ COMPLETE - Production Ready
**Last Updated:** 2026-01-08
