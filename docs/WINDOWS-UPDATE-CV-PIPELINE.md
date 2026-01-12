# Windows: Update CV Pipeline and Re-run Performance Test

**Date:** 2026-01-08
**Purpose:** Transfer updated CVPipeline fix and re-run 30-minute test

---

## Step 1: Download Updated CVPipeline

Copy and paste these commands into PowerShell (Admin):

```powershell
# Download updated pipeline from Pi
curl http://192.168.10.133:8888/cv-pipeline.tar.gz -o C:\deskpulse-build\deskpulse_installer\cv-pipeline.tar.gz

# Extract (this will update app/cv/pipeline.py)
cd C:\deskpulse-build\deskpulse_installer
tar -xzf cv-pipeline.tar.gz

# Verify file was extracted
dir app\cv\pipeline.py
```

**Expected output:** You should see `pipeline.py` file with today's date/time

---

## Step 2: Re-run 30-Minute Performance Test

```powershell
# Set Python path
$env:PYTHONPATH = "C:\deskpulse-build\deskpulse_installer"

# Run 30-minute test (this will take 30 minutes)
python windows_perf_test.py
```

---

## What to Watch For

**During the test (check every 5-10 minutes):**

1. **No errors in output** - CVPipeline should initialize without errors
2. **Memory climbing steadily** - NOT stuck at 88MB like before
3. **CPU usage showing activity** - Should see spikes during pose detection
4. **Frame processing logged** - Backend should log pose detection events

**Example of CORRECT output:**
```
[  10s] Memory:   95.2MB  CPU:  8.3%  (Avg CPU:  7.1%)
[  20s] Memory:  102.5MB  CPU: 12.1%  (Avg CPU:  9.2%)
[  30s] Memory:  108.7MB  CPU:  6.4%  (Avg CPU:  8.9%)
```

**If you see this AGAIN (WRONG):**
```
[  10s] Memory:   88.4MB  CPU:  0.2%  (Avg CPU:  0.1%)
```
This means CV pipeline is still crashing - STOP and report immediately.

---

## Success Criteria

After 30 minutes, you should see:

```
RESULTS:
  Max Memory:     <200 MB  ✅
  Avg Memory:     <150 MB  ✅
  Avg CPU:        <15%     ✅
  PASS: Memory < 200MB: True
  PASS: CPU < 15%:      True
```

**PASS = Story 8.1 Windows validation complete!**
**FAIL = Need to investigate further**

---

## If Test Fails Again

Stop immediately and report:
1. Exact error message
2. Memory/CPU values when it failed
3. How long it ran before failing

Do NOT wait 30 minutes if you see the same error pattern as before.

---

**Created:** 2026-01-08
**HTTP Server:** Running on Pi at 192.168.10.133:8888
