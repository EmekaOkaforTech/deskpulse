#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build DeskPulse Windows executable with PyInstaller.

.DESCRIPTION
    Automates the PyInstaller build process for DeskPulse Windows desktop client:
    - Validates prerequisites (Python, PyInstaller, icon file)
    - Cleans previous builds
    - Runs PyInstaller with spec file
    - Verifies build output

    Produces: dist/DeskPulse/DeskPulse.exe (one-folder distribution)

.EXAMPLE
    .\build\windows\build.ps1

.NOTES
    Requirements:
    - Python 3.9+ (64-bit)
    - PyInstaller 6.0+
    - Icon file: assets/windows/icon.ico
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
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  DeskPulse Windows Build Script" -ForegroundColor Cyan
Write-Host "  PyInstaller One-Folder Distribution" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

#
# STEP 1: Prerequisites Check
#
Write-Info "Step 1/5: Checking prerequisites..."

# Check working directory (must be project root)
if (-not (Test-Path "app/windows_client/__main__.py")) {
    Write-Error-Message "Wrong working directory!"
    Write-Host "This script must be run from the project root directory." -ForegroundColor Yellow
    Write-Host "Current directory: $PWD" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Fix: cd to project root, then run:" -ForegroundColor Yellow
    Write-Host "  .\build\windows\build.ps1" -ForegroundColor Yellow
    exit 1
}

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
if (-not (Test-Path "assets/windows/icon.ico")) {
    Write-Error-Message "Icon file not found: assets/windows/icon.ico"
    Write-Host ""
    Write-Host "Fix: Create icon file first" -ForegroundColor Yellow
    Write-Host "  python assets/windows/generate_icon.py" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "See Task 1 in story file for icon creation instructions" -ForegroundColor Yellow
    exit 1
}
Write-Success "Icon file found: assets/windows/icon.ico"

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
# STEP 2: Clean Previous Builds
#
Write-Info "Step 2/5: Cleaning previous builds..."

$cleaned = $false

if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Success "Removed dist/ directory"
    $cleaned = $true
}

if (Test-Path "build") {
    # Only remove PyInstaller build cache, not our build/windows/ directory
    if (Test-Path "build/DeskPulse") {
        Remove-Item -Recurse -Force "build/DeskPulse"
        Write-Success "Removed build/DeskPulse/ cache"
        $cleaned = $true
    }
}

if (-not $cleaned) {
    Write-Info "No previous builds to clean"
}

Write-Host ""

#
# STEP 3: Run PyInstaller Build
#
Write-Info "Step 3/5: Running PyInstaller build..."
Write-Host "This may take 2-5 minutes..." -ForegroundColor Yellow
Write-Host ""

$buildStartTime = Get-Date

# Run PyInstaller with spec file
# Capture output to log file
$logFile = "build/windows/build.log"
try {
    & pyinstaller build/windows/deskpulse.spec *>&1 | Tee-Object -FilePath $logFile

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Error-Message "Build failed!"
        Write-Host "Check build log: $logFile" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "  - Missing dependencies: pip install -r requirements.txt" -ForegroundColor Yellow
        Write-Host "  - Import errors: Add missing modules to hiddenimports in spec file" -ForegroundColor Yellow
        Write-Host "  - Icon errors: Verify assets/windows/icon.ico exists" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Error-Message "PyInstaller execution failed"
    Write-Host "Error: $_" -ForegroundColor Yellow
    exit 1
}

$buildDuration = (Get-Date) - $buildStartTime
$buildSeconds = [math]::Round($buildDuration.TotalSeconds, 1)

Write-Host ""
Write-Success "Build completed in $buildSeconds seconds"
Write-Info "Build log saved: $logFile"

Write-Host ""

#
# STEP 4: Verify Build Output
#
Write-Info "Step 4/5: Verifying build output..."

# Check executable exists
if (-not (Test-Path "dist/DeskPulse/DeskPulse.exe")) {
    Write-Error-Message "Executable not created: dist/DeskPulse/DeskPulse.exe"
    Write-Host "Check build log: $logFile" -ForegroundColor Yellow
    exit 1
}

Write-Success "Executable created: dist/DeskPulse/DeskPulse.exe"

# Get file size
$exeFile = Get-Item "dist/DeskPulse/DeskPulse.exe"
$exeSizeMB = [math]::Round($exeFile.Length / 1MB, 1)
Write-Info "Executable size: $exeSizeMB MB"

# Count total files in distribution
$fileCount = (Get-ChildItem -Recurse "dist/DeskPulse" | Where-Object { -not $_.PSIsContainer }).Count
Write-Info "Total files in distribution: $fileCount"

# Calculate total distribution size
$distSize = (Get-ChildItem -Recurse "dist/DeskPulse" | Measure-Object -Property Length -Sum).Sum
$distSizeMB = [math]::Round($distSize / 1MB, 1)
Write-Info "Total distribution size: $distSizeMB MB"

# Verify icon in assets
if (Test-Path "dist/DeskPulse/assets/icon.ico") {
    Write-Success "Icon bundled in distribution"
} else {
    Write-Warning "Icon not found in dist/DeskPulse/assets/icon.ico"
}

Write-Host ""

#
# STEP 5: Build Summary
#
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  ✅ Build Successful!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Executable:    dist/DeskPulse/DeskPulse.exe" -ForegroundColor Cyan
Write-Host "File size:     $exeSizeMB MB" -ForegroundColor Cyan
Write-Host "Total files:   $fileCount files in dist/DeskPulse/" -ForegroundColor Cyan
Write-Host "Dist size:     $distSizeMB MB" -ForegroundColor Cyan
Write-Host "Build time:    $buildSeconds seconds" -ForegroundColor Cyan
Write-Host "Build log:     $logFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test:   .\dist\DeskPulse\DeskPulse.exe" -ForegroundColor White
Write-Host "  2. Create installer: Run Inno Setup on build/windows/installer.iss" -ForegroundColor White
Write-Host ""
