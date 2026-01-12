# Fix CVPipeline on Windows - Copy/Paste Method

**Network transfer not working - use this manual method instead**

---

## Step 1: Create Fix Script on Windows

Open PowerShell (Admin) and run:

```powershell
cd C:\deskpulse-build\deskpulse_installer
```

Create file `fix_pipeline.py` with this content (copy/paste into notepad, save as fix_pipeline.py):

```python
"""Auto-patch CVPipeline for Windows Camera Support"""
import shutil
from pathlib import Path

pipeline_path = Path(r"C:\deskpulse-build\deskpulse_installer\app\cv\pipeline.py")
print(f"Patching: {pipeline_path}")

# Backup
backup_path = pipeline_path.with_suffix('.py.backup')
shutil.copy2(pipeline_path, backup_path)
print(f"Backup: {backup_path}")

content = pipeline_path.read_text(encoding='utf-8')

# Fix 1: Add camera parameter
content = content.replace(
    'def __init__(self, fps_target: int = 10, app=None):',
    'def __init__(self, fps_target: int = 10, app=None, camera=None):'
)

# Fix 2: Track external camera
content = content.replace(
    '        self.app = app  # Store Flask app for background thread app context\n        self.camera = None',
    '        self.app = app  # Store Flask app for background thread app context\n        self.camera = camera  # Story 8.1\n        self.external_camera = camera is not None'
)

# Fix 3: Don't overwrite external camera
content = content.replace(
    '            self.camera = CameraCapture()',
    '            if not self.external_camera:\n                self.camera = CameraCapture()'
)

# Fix 4: Handle camera.read() vs camera.read_frame()
content = content.replace(
    '                # Attempt frame capture\n                ret, frame = self.camera.read_frame()',
    '                # Attempt frame capture\n                if self.external_camera:\n                    ret, frame = self.camera.read()\n                else:\n                    ret, frame = self.camera.read_frame()'
)

# Write patched file
pipeline_path.write_text(content, encoding='utf-8')
print("✓ Patched!")
```

---

## Step 2: Run the Fix Script

```powershell
python fix_pipeline.py
```

**Expected output:**
```
Patching: C:\deskpulse-build\deskpulse_installer\app\cv\pipeline.py
Backup: C:\deskpulse-build\deskpulse_installer\app\cv\pipeline.py.backup
✓ Patched!
```

---

## Step 3: Run 30-Minute Test

```powershell
$env:PYTHONPATH = "C:\deskpulse-build\deskpulse_installer"
python windows_perf_test.py
```

**This time you should see:**
- ✅ No CVPipeline errors
- ✅ Camera opens successfully
- ✅ Memory climbs above 88MB (actual CV processing)
- ✅ CPU shows activity (pose detection)

---

## If Patch Script Fails

The script is a simple text replacement. If it fails, manually edit `app\cv\pipeline.py`:

1. Line 61: Change `def __init__(self, fps_target: int = 10, app=None):` to include `, camera=None`
2. Line 80: Change `self.camera = None` to `self.camera = camera`
3. Add line: `self.external_camera = camera is not None`
4. Line 132: Change `self.camera = CameraCapture()` to check if external camera first

See `docs/PIPELINE-FIX-WINDOWS.md` for detailed manual instructions.

---

**Created:** 2026-01-08
**Issue:** Network transfer blocked, using copy/paste method
