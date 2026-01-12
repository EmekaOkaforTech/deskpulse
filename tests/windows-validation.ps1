# Story 8.3 Windows Validation Script
# Run from project root: .\tests\windows-validation.ps1

$ErrorActionPreference = "Continue"

# Create output directory if it doesn't exist
$OutputDir = "docs\sprint-artifacts"
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$OutputFile = "$OutputDir\validation-report-8-3-windows-$(Get-Date -Format 'yyyy-MM-dd-HHmm').md"

Write-Host "=== Story 8.3 Windows Validation ===" -ForegroundColor Cyan
Write-Host "Output: $OutputFile`n" -ForegroundColor Yellow

# Start report
@"
# Story 8.3 Windows Validation Report
**Date:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')
**Tester:** $env:USERNAME
**Machine:** $env:COMPUTERNAME

---

## System Information
"@ | Out-File $OutputFile -Encoding UTF8

# Collect system info
Write-Host "[1/9] Collecting system info..." -ForegroundColor Green
$winVersion = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").ProductName
$winBuild = (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").CurrentBuild
$pythonVersion = & python --version 2>&1
@"
- **OS:** $winVersion
- **Build:** $winBuild
- **Python:** $pythonVersion
- **Working Directory:** $(Get-Location)

---

## Test Results

### Unit Tests

"@ | Add-Content $OutputFile -Encoding UTF8

# Run unit tests
Write-Host "[2/11] Running unit tests (camera_detection)..." -ForegroundColor Green
$test1Output = & pytest tests/test_camera_detection.py -v 2>&1
$test1 = $test1Output | Out-String
"#### test_camera_detection.py`n``````text`n$test1`n```````n" | Add-Content $OutputFile -Encoding UTF8

Write-Host "[3/11] Running unit tests (camera_selection_dialog)..." -ForegroundColor Green
$test2Output = & pytest tests/test_camera_selection_dialog.py -v 2>&1
$test2 = $test2Output | Out-String
"#### test_camera_selection_dialog.py`n``````text`n$test2`n```````n" | Add-Content $OutputFile -Encoding UTF8

Write-Host "[4/11] Running unit tests (camera_permissions)..." -ForegroundColor Green
$test3Output = & pytest tests/test_camera_permissions.py -v 2>&1
$test3 = $test3Output | Out-String
"#### test_camera_permissions.py`n``````text`n$test3`n```````n" | Add-Content $OutputFile -Encoding UTF8

Write-Host "[5/11] Running unit tests (camera_error_handler)..." -ForegroundColor Green
$test5Output = & pytest tests/test_camera_error_handler.py -v 2>&1
$test5 = $test5Output | Out-String
"#### test_camera_error_handler.py`n``````text`n$test5`n```````n" | Add-Content $OutputFile -Encoding UTF8

Write-Host "[6/11] Running unit tests (camera_thread_safety)..." -ForegroundColor Green
$test6Output = & pytest tests/test_camera_thread_safety.py -v 2>&1
$test6 = $test6Output | Out-String
"#### test_camera_thread_safety.py`n``````text`n$test6`n```````n" | Add-Content $OutputFile -Encoding UTF8

# Run integration tests
Write-Host "[7/11] Running integration tests..." -ForegroundColor Green
$test4Output = & pytest tests/test_windows_camera_integration.py -v 2>&1
$test4 = $test4Output | Out-String
"### Integration Tests`n``````text`n$test4`n```````n" | Add-Content $OutputFile -Encoding UTF8

# Manual camera detection
Write-Host "[8/11] Testing camera detection..." -ForegroundColor Green
$cameraDetectOutput = & python -c "from app.standalone.camera_windows import detect_cameras_with_names; import json; print(json.dumps(detect_cameras_with_names(), indent=2))" 2>&1
$cameraDetect = $cameraDetectOutput | Out-String
@"

---

## Manual Tests

### Camera Detection
``````text
$cameraDetect
``````

"@ | Add-Content $OutputFile -Encoding UTF8

# Manual permissions check
Write-Host "[9/11] Testing camera permissions..." -ForegroundColor Green
$permissionsOutput = & python -c "from app.standalone.camera_permissions import check_camera_permissions; import json; print(json.dumps(check_camera_permissions(), indent=2))" 2>&1
$permissions = $permissionsOutput | Out-String
@"
### Camera Permissions
``````text
$permissions
``````

"@ | Add-Content $OutputFile -Encoding UTF8

# Manual camera opening test
Write-Host "[10/11] Testing camera opening (may take 5-30 seconds)..." -ForegroundColor Green
$cameraOpenOutput = & python -c "from app.standalone.camera_windows import WindowsCamera; cam = WindowsCamera(0); result = cam.open(); print(f'Opened: {result}'); cam.release()" 2>&1
$cameraOpen = $cameraOpenOutput | Out-String
@"
### Camera Opening Test
``````text
$cameraOpen
``````

"@ | Add-Content $OutputFile -Encoding UTF8

# Summary
Write-Host "[11/11] Generating summary..." -ForegroundColor Green

# Count test results
$passedCount = 0
$failedCount = 0

if ($test1 -match "(\d+) passed") { $passedCount += [int]$Matches[1] }
if ($test2 -match "(\d+) passed") { $passedCount += [int]$Matches[1] }
if ($test3 -match "(\d+) passed") { $passedCount += [int]$Matches[1] }
if ($test4 -match "(\d+) passed") { $passedCount += [int]$Matches[1] }
if ($test5 -match "(\d+) passed") { $passedCount += [int]$Matches[1] }
if ($test6 -match "(\d+) passed") { $passedCount += [int]$Matches[1] }

if ($test1 -match "(\d+) failed") { $failedCount += [int]$Matches[1] }
if ($test2 -match "(\d+) failed") { $failedCount += [int]$Matches[1] }
if ($test3 -match "(\d+) failed") { $failedCount += [int]$Matches[1] }
if ($test4 -match "(\d+) failed") { $failedCount += [int]$Matches[1] }
if ($test5 -match "(\d+) failed") { $failedCount += [int]$Matches[1] }
if ($test6 -match "(\d+) failed") { $failedCount += [int]$Matches[1] }

@"

---

## Summary
- **Tests Passed:** $passedCount
- **Tests Failed:** $failedCount
- **Status:** $(if ($failedCount -eq 0) { "✅ ALL PASSED" } else { "❌ $failedCount FAILED" })

---

## Next Steps
1. Review failures (if any) above
2. Run 30-minute stability test: ``python tests/windows_perf_test.py --duration 1800``
3. Repeat on Windows 11 machine (if this is Windows 10)
4. Commit results: ``git add . && git commit -m "Story 8.3: Windows validation complete" && git push``

**Validation Complete: $(Get-Date -Format 'yyyy-MM-dd HH:mm')**
"@ | Add-Content $OutputFile -Encoding UTF8

Write-Host "`n✅ Validation complete!" -ForegroundColor Green
Write-Host "Report saved: $OutputFile" -ForegroundColor Yellow
Write-Host "`nTo view report:" -ForegroundColor Cyan
Write-Host "  notepad `"$OutputFile`"" -ForegroundColor White
