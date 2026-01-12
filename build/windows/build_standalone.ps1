#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build DeskPulse Standalone Windows executable with PyInstaller.

.DESCRIPTION
    Automates the PyInstaller build process for DeskPulse Standalone Edition:
    - Validates prerequisites (Python, PyInstaller, icon file, Story 8.5 code)
    - Checks backend dependencies (Flask, OpenCV, MediaPipe)
    - Handles Epic 7 hook conflicts (temporarily renames hook-app.py)
    - Cleans previous builds
    - Runs PyInstaller with standalone.spec
    - Verifies build output (including backend DLLs)
    - Restores Epic 7 hook

    Produces: dist/DeskPulse-Standalone/DeskPulse.exe (one-folder distribution)

.EXAMPLE
    .\build\windows\build_standalone.ps1

.NOTES
    Requirements:
    - Python 3.9+ (64-bit)
    - PyInstaller 6.0+
    - Icon file: assets/windows/icon_professional.ico
    - Story 8.5 complete: app/standalone/__main__.py
    - Backend dependencies: Flask, opencv-python, mediapipe
    - Working directory: Project root
#>

# Exit on any error
$ErrorActionPreference = "Stop"

# Color output functions
function Write-Success { param($Message) Write-Host "✅ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ️  $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠️  $Message" -ForegroundColor Yellow }
function Write-Error-Message { param($Message) Write-Host "❌ $Message" -ForegroundColor Red }

# Header
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  DeskPulse Standalone Edition Build Script" -ForegroundColor Cyan
Write-Host "  PyInstaller One-Folder Distribution (Full Backend)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

#
# STEP 1: Prerequisites Check
#
Write-Info "Step 1/7: Checking prerequisites..."

# Check PowerShell execution policy
$policy = Get-ExecutionPolicy
if ($policy -eq "Restricted" -or $policy -eq "AllSigned") {
    Write-Warning "PowerShell execution policy restrictive: $policy"
    Write-Host "If script fails, run with:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File build/windows/build_standalone.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Check working directory (must be project root)
if (-not (Test-Path "app/standalone/__main__.py")) {
    Write-Error-Message "Story 8.5 entry point not found!"
    Write-Host ""
    if (Test-Path "app") {
        Write-Host "Found app/ directory but missing: app/standalone/__main__.py" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "CRITICAL: Story 8.5 must be complete before building Story 8.6" -ForegroundColor Red
        Write-Host "Required Story 8.5 files:" -ForegroundColor Yellow
        Write-Host "  - app/standalone/__main__.py" -ForegroundColor Yellow
        Write-Host "  - app/standalone/backend_thread.py" -ForegroundColor Yellow
        Write-Host "  - app/standalone/tray_app.py" -ForegroundColor Yellow
        Write-Host "  - app/standalone/config.py" -ForegroundColor Yellow
    } else {
        Write-Host "Wrong working directory!" -ForegroundColor Yellow
        Write-Host "Current directory: $PWD" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Fix: cd to project root, then run:" -ForegroundColor Yellow
        Write-Host "  .\build\windows\build_standalone.ps1" -ForegroundColor Yellow
    }
    exit 1
}
Write-Success "Story 8.5 entry point found: app/standalone/__main__.py"

# Verify Story 8.5 components
$story85Files = @(
    "app/standalone/backend_thread.py",
    "app/standalone/tray_app.py",
    "app/standalone/config.py",
    "app/standalone/camera_windows.py"
)

$missingFiles = @()
foreach ($file in $story85Files) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Error-Message "Story 8.5 components missing!"
    Write-Host ""
    Write-Host "Missing files:" -ForegroundColor Yellow
    foreach ($file in $missingFiles) {
        Write-Host "  - $file" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Story 8.5 must be complete before building Story 8.6" -ForegroundColor Red
    exit 1
}
Write-Success "All Story 8.5 components present"

# Check Python version (64-bit, 3.9+)
try {
    $pythonVersion = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Python not found" }

    Write-Success "Python found: $pythonVersion"

    # Parse version
    if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]

        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
            Write-Error-Message "Python 3.9+ required, found: $pythonVersion"
            Write-Host "Download Python 3.9+ (64-bit): https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
    }

    # Check if 64-bit
    $pythonArch = & python -c "import platform; print(platform.architecture()[0])"
    if ($pythonArch -ne "64bit") {
        Write-Error-Message "Python 64-bit required, found: $pythonArch"
        Write-Host "Download Python 3.9+ (64-bit): https://www.python.org/downloads/" -ForegroundColor Yellow
        exit 1
    }
    Write-Success "Python architecture: $pythonArch"
} catch {
    Write-Error-Message "Python not found"
    Write-Host "Install Python 3.9+ (64-bit): https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check icon file exists
if (-not (Test-Path "assets/windows/icon_professional.ico")) {
    Write-Error-Message "Icon file not found: assets/windows/icon_professional.ico"
    Write-Host ""
    Write-Host "This icon was created in Epic 7 and should exist." -ForegroundColor Yellow
    Write-Host "If missing, check Epic 7 build artifacts." -ForegroundColor Yellow
    exit 1
}
Write-Success "Icon file found: assets/windows/icon_professional.ico"

# Check PyInstaller available (install if missing)
try {
    $pyinstallerCheck = & pip show pyinstaller 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "PyInstaller not found, installing..."
        & pip install pyinstaller
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Message "Failed to install PyInstaller"
            Write-Host "Try manually: pip install pyinstaller" -ForegroundColor Yellow
            exit 1
        }
    }

    # Get PyInstaller version
    $pyinstallerVersion = & pip show pyinstaller | Select-String "Version:" | ForEach-Object { $_ -replace "Version: ", "" }
    Write-Success "PyInstaller found: v$pyinstallerVersion"

    # Check version >= 6.0
    if ($pyinstallerVersion -match "(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        if ($major -lt 6) {
            Write-Warning "PyInstaller 6.0+ recommended, found: v$pyinstallerVersion"
            Write-Host "Update recommended: pip install --upgrade pyinstaller" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Error-Message "Failed to check PyInstaller"
    Write-Host "Try: pip install pyinstaller" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

#
# STEP 2: Check Backend Dependencies
#
Write-Info "Step 2/7: Verifying backend dependencies..."

$backendPackages = @{
    "flask" = "Flask web framework"
    "opencv-python" = "OpenCV computer vision"
    "mediapipe" = "MediaPipe pose detection"
    "pystray" = "System tray support"
    "winotify" = "Toast notifications"
    "pywin32" = "Windows API access"
}

$missingPackages = @()
foreach ($pkg in $backendPackages.Keys) {
    try {
        $null = & pip show $pkg 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "$($backendPackages[$pkg]): $pkg installed"
        } else {
            $missingPackages += $pkg
        }
    } catch {
        $missingPackages += $pkg
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Error-Message "Backend packages missing!"
    Write-Host ""
    Write-Host "Missing packages:" -ForegroundColor Yellow
    foreach ($pkg in $missingPackages) {
        Write-Host "  - $pkg ($($backendPackages[$pkg]))" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Fix: Install dependencies" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor White
    Write-Host "  pip install -r requirements-windows.txt" -ForegroundColor White
    exit 1
}

Write-Host ""

#
# STEP 3: Handle Epic 7 Hook Conflicts
#
Write-Info "Step 3/7: Handling PyInstaller hook conflicts..."

# Epic 7 hook-app.py EXCLUDES server modules (Flask, cv2)
# Standalone needs server modules INCLUDED
# Solution: Temporarily rename hook to prevent conflicts

$epic7Hook = "build/windows/hook-app.py"
$epic7HookBackup = "build/windows/hook-app.py.epic7.bak"

if (Test-Path $epic7Hook) {
    Write-Warning "Found Epic 7 hook (excludes server modules)"
    Write-Info "Temporarily renaming to prevent conflicts..."

    try {
        Rename-Item -Path $epic7Hook -NewName "hook-app.py.epic7.bak" -Force
        Write-Success "Epic 7 hook renamed: hook-app.py.epic7.bak"
        Write-Info "Will restore after build completes"
    } catch {
        Write-Error-Message "Failed to rename Epic 7 hook"
        Write-Host "Error: $_" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Manual fix: Rename or delete build/windows/hook-app.py before building" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Info "No Epic 7 hook found (expected if Epic 7 not built)"
}

Write-Host ""

#
# STEP 4: Clean Previous Builds
#
Write-Info "Step 4/7: Cleaning previous builds..."

$cleaned = $false

if (Test-Path "dist/DeskPulse-Standalone") {
    Remove-Item -Recurse -Force "dist/DeskPulse-Standalone"
    Write-Success "Removed dist/DeskPulse-Standalone/ directory"
    $cleaned = $true
}

# Only remove PyInstaller build cache for standalone, not Epic 7 client
if (Test-Path "build/DeskPulse-Standalone") {
    Remove-Item -Recurse -Force "build/DeskPulse-Standalone"
    Write-Success "Removed build/DeskPulse-Standalone/ cache"
    $cleaned = $true
}

if (-not $cleaned) {
    Write-Info "No previous builds to clean"
}

Write-Host ""

#
# STEP 5: Run PyInstaller Build
#
Write-Info "Step 5/7: Running PyInstaller build..."
Write-Host "This may take 3-7 minutes (backend bundling)..." -ForegroundColor Yellow
Write-Host ""

$buildStartTime = Get-Date

# Run PyInstaller with standalone spec file
# Capture output to log file
$logFile = "build/windows/build_standalone.log"
try {
    & pyinstaller build/windows/standalone.spec *>&1 | Tee-Object -FilePath $logFile

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Error-Message "Build failed!"
        Write-Host "Check build log: $logFile" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "  - Missing dependencies: pip install -r requirements.txt requirements-windows.txt" -ForegroundColor Yellow
        Write-Host "  - Import errors: Add missing modules to hiddenimports in standalone.spec" -ForegroundColor Yellow
        Write-Host "  - Icon errors: Verify assets/windows/icon_professional.ico exists" -ForegroundColor Yellow
        Write-Host "  - MediaPipe errors: Verify mediapipe==0.10.31 installed (x64)" -ForegroundColor Yellow

        # Restore Epic 7 hook before exit
        if (Test-Path $epic7HookBackup) {
            Rename-Item -Path $epic7HookBackup -NewName "hook-app.py" -Force
            Write-Info "Restored Epic 7 hook"
        }

        exit 1
    }
} catch {
    Write-Error-Message "PyInstaller execution failed"
    Write-Host "Error: $_" -ForegroundColor Yellow

    # Restore Epic 7 hook before exit
    if (Test-Path $epic7HookBackup) {
        Rename-Item -Path $epic7HookBackup -NewName "hook-app.py" -Force
        Write-Info "Restored Epic 7 hook"
    }

    exit 1
}

$buildDuration = (Get-Date) - $buildStartTime
$buildSeconds = [math]::Round($buildDuration.TotalSeconds, 1)

Write-Host ""
Write-Success "Build completed in $buildSeconds seconds"
Write-Info "Build log saved: $logFile"

Write-Host ""

#
# STEP 6: Verify Build Output
#
Write-Info "Step 6/7: Verifying build output..."

# Check executable exists
if (-not (Test-Path "dist/DeskPulse-Standalone/DeskPulse.exe")) {
    Write-Error-Message "Executable not created: dist/DeskPulse-Standalone/DeskPulse.exe"
    Write-Host "Check build log: $logFile" -ForegroundColor Yellow

    # Restore Epic 7 hook before exit
    if (Test-Path $epic7HookBackup) {
        Rename-Item -Path $epic7HookBackup -NewName "hook-app.py" -Force
    }

    exit 1
}

Write-Success "Executable created: dist/DeskPulse-Standalone/DeskPulse.exe"

# Get file size
$exeFile = Get-Item "dist/DeskPulse-Standalone/DeskPulse.exe"
$exeSizeMB = [math]::Round($exeFile.Length / 1MB, 1)
Write-Info "Executable size: $exeSizeMB MB"

# Count total files in distribution
$fileCount = (Get-ChildItem -Recurse "dist/DeskPulse-Standalone" | Where-Object { -not $_.PSIsContainer }).Count
Write-Info "Total files in distribution: $fileCount"

# Calculate total distribution size
$distSize = (Get-ChildItem -Recurse "dist/DeskPulse-Standalone" | Measure-Object -Property Length -Sum).Sum
$distSizeMB = [math]::Round($distSize / 1MB, 1)
Write-Info "Total distribution size: $distSizeMB MB"

# Verify icon in assets
if (Test-Path "dist/DeskPulse-Standalone/assets/windows/icon_professional.ico") {
    Write-Success "Icon bundled in distribution"
} else {
    Write-Warning "Icon not found in dist/DeskPulse-Standalone/assets/windows/icon_professional.ico"
}

# Verify backend DLLs bundled (CRITICAL for standalone)
Write-Info "Verifying backend components bundled..."

$backendChecks = @{
    "cv2" = "dist/DeskPulse-Standalone/_internal/cv2"
    "mediapipe" = "dist/DeskPulse-Standalone/_internal/mediapipe"
    "flask" = "dist/DeskPulse-Standalone/_internal/flask"
}

foreach ($component in $backendChecks.Keys) {
    $path = $backendChecks[$component]
    if (Test-Path $path) {
        Write-Success "Backend component bundled: $component"
    } else {
        Write-Warning "Backend component missing: $component (path: $path)"
        Write-Host "Build may fail at runtime - verify hiddenimports in standalone.spec" -ForegroundColor Yellow
    }
}

# Size expectations check
if ($distSizeMB -lt 150) {
    Write-Warning "Distribution size unexpectedly small: $distSizeMB MB"
    Write-Host "Expected: 200-300 MB (full backend bundled)" -ForegroundColor Yellow
    Write-Host "Backend components may be missing - verify at runtime" -ForegroundColor Yellow
} elseif ($distSizeMB -gt 400) {
    Write-Warning "Distribution size larger than expected: $distSizeMB MB"
    Write-Host "Expected: 200-300 MB" -ForegroundColor Yellow
    Write-Host "Check for unnecessary dependencies or duplicate DLLs" -ForegroundColor Yellow
} else {
    Write-Success "Distribution size within expected range (200-300 MB)"
}

Write-Host ""

#
# STEP 7: Restore Epic 7 Hook
#
Write-Info "Step 7/7: Restoring Epic 7 hook..."

if (Test-Path $epic7HookBackup) {
    try {
        Rename-Item -Path $epic7HookBackup -NewName "hook-app.py" -Force
        Write-Success "Epic 7 hook restored: hook-app.py"
    } catch {
        Write-Warning "Failed to restore Epic 7 hook"
        Write-Host "Manual fix: Rename hook-app.py.epic7.bak to hook-app.py" -ForegroundColor Yellow
    }
} else {
    Write-Info "No Epic 7 hook to restore"
}

Write-Host ""

#
# Build Summary
#
Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  ✅ Build Successful!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Executable:       dist/DeskPulse-Standalone/DeskPulse.exe" -ForegroundColor Cyan
Write-Host "Exe size:         $exeSizeMB MB" -ForegroundColor Cyan
Write-Host "Total files:      $fileCount files" -ForegroundColor Cyan
Write-Host "Dist size:        $distSizeMB MB" -ForegroundColor Cyan
Write-Host "Build time:       $buildSeconds seconds" -ForegroundColor Cyan
Write-Host "Build log:        $logFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test standalone:  .\dist\DeskPulse-Standalone\DeskPulse.exe" -ForegroundColor White
Write-Host "  2. Create installer: iscc build\windows\installer_standalone.iss" -ForegroundColor White
Write-Host "  3. Test on clean Windows 10/11 VM (CRITICAL - no Python required)" -ForegroundColor White
Write-Host ""
