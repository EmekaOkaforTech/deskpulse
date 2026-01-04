# Story 7.2 Automated Validation Script (Windows PowerShell)
# Automates validation checks that don't require manual interaction

param(
    [string]$PiBackendUrl = "http://raspberrypi.local:5000",
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ValidationResults = @()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Story 7.2 Automated Validation" -ForegroundColor Cyan
Write-Host "Windows Toast Notifications" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Function to log validation result
function Add-ValidationResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Details = ""
    )

    $result = [PSCustomObject]@{
        Test = $TestName
        Passed = $Passed
        Details = $Details
    }

    $script:ValidationResults += $result

    if ($Passed) {
        Write-Host "[PASS] $TestName" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $TestName" -ForegroundColor Red
    }

    if ($Details -and $Verbose) {
        Write-Host "       $Details" -ForegroundColor Gray
    }
}

# Test 1: Python Environment
Write-Host "`n=== Python Environment ===" -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    $versionMatch = $pythonVersion -match "Python 3\.([0-9]+)\."
    $minorVersion = if ($versionMatch) { [int]$Matches[1] } else { 0 }

    if ($minorVersion -ge 9) {
        Add-ValidationResult -TestName "Python 3.9+ installed" -Passed $true -Details $pythonVersion
    } else {
        Add-ValidationResult -TestName "Python 3.9+ installed" -Passed $false -Details "Found: $pythonVersion, Required: Python 3.9+"
    }
} catch {
    Add-ValidationResult -TestName "Python 3.9+ installed" -Passed $false -Details "Python not found in PATH"
}

# Test 2: Required Python Packages
Write-Host "`n=== Python Dependencies ===" -ForegroundColor Yellow
$requiredPackages = @("winotify", "python-socketio", "requests", "pywin32")

foreach ($package in $requiredPackages) {
    try {
        $installed = pip show $package 2>&1
        if ($LASTEXITCODE -eq 0) {
            Add-ValidationResult -TestName "Package: $package" -Passed $true
        } else {
            Add-ValidationResult -TestName "Package: $package" -Passed $false -Details "Not installed (run: pip install $package)"
        }
    } catch {
        Add-ValidationResult -TestName "Package: $package" -Passed $false -Details "Error checking package"
    }
}

# Test 3: Backend Reachability
Write-Host "`n=== Backend Connectivity ===" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $PiBackendUrl -Method Head -TimeoutSec 5 -ErrorAction Stop
    Add-ValidationResult -TestName "Backend reachable at $PiBackendUrl" -Passed $true -Details "Status: $($response.StatusCode)"
} catch {
    Add-ValidationResult -TestName "Backend reachable at $PiBackendUrl" -Passed $false -Details $_.Exception.Message
}

# Test 4: Config File Exists
Write-Host "`n=== Configuration Files ===" -ForegroundColor Yellow
$configPath = "$env:APPDATA\DeskPulse\config.json"
if (Test-Path $configPath) {
    try {
        $config = Get-Content $configPath | ConvertFrom-Json
        Add-ValidationResult -TestName "Config file exists" -Passed $true -Details $configPath

        if ($config.backend_url) {
            Add-ValidationResult -TestName "Config has backend_url" -Passed $true -Details $config.backend_url
        } else {
            Add-ValidationResult -TestName "Config has backend_url" -Passed $false -Details "backend_url field missing"
        }
    } catch {
        Add-ValidationResult -TestName "Config file valid JSON" -Passed $false -Details $_.Exception.Message
    }
} else {
    Add-ValidationResult -TestName "Config file exists" -Passed $false -Details "Not found: $configPath (run client once to create)"
}

# Test 5: Log Directory
Write-Host "`n=== Logging Setup ===" -ForegroundColor Yellow
$logDir = "$env:APPDATA\DeskPulse\logs"
if (Test-Path $logDir) {
    Add-ValidationResult -TestName "Log directory exists" -Passed $true -Details $logDir

    $logFile = "$logDir\client.log"
    if (Test-Path $logFile) {
        $logSize = (Get-Item $logFile).Length
        Add-ValidationResult -TestName "Client log file exists" -Passed $true -Details "Size: $logSize bytes"
    } else {
        Add-ValidationResult -TestName "Client log file exists" -Passed $false -Details "Not found (client not run yet)"
    }
} else {
    Add-ValidationResult -TestName "Log directory exists" -Passed $false -Details "Client not run yet"
}

# Test 6: Code Files Exist
Write-Host "`n=== Implementation Files ===" -ForegroundColor Yellow
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$requiredFiles = @(
    "app\windows_client\notifier.py",
    "app\windows_client\socketio_client.py",
    "app\windows_client\__main__.py",
    "tests\test_windows_notifier.py",
    "tests\test_backend_socketio_events.py"
)

foreach ($file in $requiredFiles) {
    $fullPath = Join-Path $projectRoot $file
    if (Test-Path $fullPath) {
        Add-ValidationResult -TestName "File: $file" -Passed $true
    } else {
        Add-ValidationResult -TestName "File: $file" -Passed $false -Details "Missing"
    }
}

# Test 7: Code Quality Checks
Write-Host "`n=== Code Structure Validation ===" -ForegroundColor Yellow

# Check for broadcast=True in alert_triggered
$pipelinePath = Join-Path $projectRoot "app\cv\pipeline.py"
if (Test-Path $pipelinePath) {
    $pipelineContent = Get-Content $pipelinePath -Raw
    if ($pipelineContent -match "socketio\.emit\('alert_triggered'.*broadcast=True") {
        Add-ValidationResult -TestName "alert_triggered uses broadcast=True" -Passed $true
    } else {
        Add-ValidationResult -TestName "alert_triggered uses broadcast=True" -Passed $false -Details "CRITICAL: broadcast=True missing"
    }
} else {
    Add-ValidationResult -TestName "alert_triggered uses broadcast=True" -Passed $false -Details "pipeline.py not found"
}

# Check for event handlers in socketio_client.py
$socketioClientPath = Join-Path $projectRoot "app\windows_client\socketio_client.py"
if (Test-Path $socketioClientPath) {
    $socketioContent = Get-Content $socketioClientPath -Raw

    $handlers = @("on_alert_triggered", "on_posture_corrected")
    foreach ($handler in $handlers) {
        if ($socketioContent -match "def $handler") {
            Add-ValidationResult -TestName "Handler: $handler exists" -Passed $true
        } else {
            Add-ValidationResult -TestName "Handler: $handler exists" -Passed $false -Details "Missing handler method"
        }
    }
} else {
    Add-ValidationResult -TestName "socketio_client.py exists" -Passed $false
}

# Test 8: Unit Tests
Write-Host "`n=== Unit Test Execution ===" -ForegroundColor Yellow
Push-Location $projectRoot
try {
    $env:PYTHONPATH = $projectRoot

    # Run notifier tests
    Write-Host "Running test_windows_notifier.py..." -ForegroundColor Gray
    $notifierTestResult = python -m pytest tests\test_windows_notifier.py -v --tb=short 2>&1
    $notifierPassed = $LASTEXITCODE -eq 0
    Add-ValidationResult -TestName "WindowsNotifier unit tests (23 tests)" -Passed $notifierPassed -Details $(if ($notifierPassed) { "All tests passed" } else { "Tests failed - check output" })

    # Run backend event tests
    Write-Host "Running test_backend_socketio_events.py..." -ForegroundColor Gray
    $backendTestResult = python -m pytest tests\test_backend_socketio_events.py -v --tb=short 2>&1
    $backendPassed = $LASTEXITCODE -eq 0
    Add-ValidationResult -TestName "Backend SocketIO event tests (6 tests)" -Passed $backendPassed -Details $(if ($backendPassed) { "All tests passed" } else { "Tests failed - check output" })

} catch {
    Add-ValidationResult -TestName "Unit test execution" -Passed $false -Details $_.Exception.Message
} finally {
    Pop-Location
}

# Summary Report
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$totalTests = $ValidationResults.Count
$passedTests = ($ValidationResults | Where-Object { $_.Passed }).Count
$failedTests = $totalTests - $passedTests

Write-Host "`nTotal Tests: $totalTests" -ForegroundColor White
Write-Host "Passed:      $passedTests" -ForegroundColor Green
Write-Host "Failed:      $failedTests" -ForegroundColor $(if ($failedTests -gt 0) { "Red" } else { "Green" })

if ($failedTests -gt 0) {
    Write-Host "`nFailed Tests:" -ForegroundColor Red
    $ValidationResults | Where-Object { -not $_.Passed } | ForEach-Object {
        Write-Host "  - $($_.Test)" -ForegroundColor Red
        if ($_.Details) {
            Write-Host "    $($_.Details)" -ForegroundColor Gray
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
if ($failedTests -eq 0) {
    Write-Host "✅ ALL AUTOMATED CHECKS PASSED" -ForegroundColor Green
    Write-Host "`nNext Steps:" -ForegroundColor Yellow
    Write-Host "1. Run Windows desktop client: python -m app.windows_client" -ForegroundColor White
    Write-Host "2. Complete manual validation: tests\manual\STORY-7-2-MANUAL-VALIDATION.md" -ForegroundColor White
} else {
    Write-Host "❌ VALIDATION FAILED" -ForegroundColor Red
    Write-Host "`nFix failed checks before manual testing." -ForegroundColor Yellow
    exit 1
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
