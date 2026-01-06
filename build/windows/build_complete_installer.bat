@echo off
REM Complete DeskPulse Installer Builder
REM Step 1: Build Windows client as standalone .exe
REM Step 2: Create payload with .exe (not source code)
REM Step 3: Build installer that bundles payload

echo ========================================
echo DeskPulse Complete Installer Builder
echo ========================================
echo.

REM Check if running from project root
cd /d "%~dp0\..\..
if not exist "app\windows_client" (
    echo ERROR: Must run from deskpulse project root!
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo [1/6] Building Windows client as standalone .exe...
call build\windows\build_client_exe.bat
if errorlevel 1 (
    echo ERROR: Client build failed
    pause
    exit /b 1
)

echo.
echo [2/6] Creating payload directory...
if exist "build\windows\payload_temp" rmdir /S /Q "build\windows\payload_temp"
mkdir "build\windows\payload_temp"

REM Copy standalone .exe
copy /Y "dist\DeskPulse.exe" "build\windows\payload_temp\"

REM Copy launcher script (updated to run .exe)
copy /Y "build\windows\start_deskpulse.vbs" "build\windows\payload_temp\"

REM Copy icon
mkdir "build\windows\payload_temp\assets\windows"
copy /Y "assets\windows\icon_professional.ico" "build\windows\payload_temp\assets\windows\"

echo Payload contents:
dir /B "build\windows\payload_temp"

echo.
echo [3/6] Creating payload.zip...
cd build\windows\payload_temp
powershell -Command "Compress-Archive -Path * -DestinationPath ..\payload.zip -Force"
cd ..\..\..

if not exist "build\windows\payload.zip" (
    echo ERROR: Failed to create payload.zip
    pause
    exit /b 1
)
echo Payload created: build\windows\payload.zip

REM Clean up temp directory
rmdir /S /Q "build\windows\payload_temp"

echo.
echo [4/6] Building installer with PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "DeskPulse-Setup" ^
    --icon "assets\windows\icon_professional.ico" ^
    --add-data "build\windows\payload.zip;." ^
    build\windows\installer_wrapper.py ^
    --clean

if errorlevel 1 (
    echo ERROR: Installer build failed
    pause
    exit /b 1
)

echo.
echo [5/6] Verifying installer...
if not exist "dist\DeskPulse-Setup.exe" (
    echo ERROR: DeskPulse-Setup.exe not found
    pause
    exit /b 1
)

echo Installer verified: dist\DeskPulse-Setup.exe
dir dist\DeskPulse-Setup.exe | find "DeskPulse-Setup.exe"

echo.
echo [6/6] Cleaning up...
del /Q "build\windows\payload.zip"
del /Q "dist\DeskPulse.exe"
rmdir /S /Q "build\DeskPulse"
echo Temporary files removed

echo.
echo ========================================
echo Complete Build Successful!
echo ========================================
echo.
echo Installer: dist\DeskPulse-Setup.exe
echo.
echo What's included:
echo   - Standalone DeskPulse.exe (no Python needed)
echo   - Professional icon
echo   - Silent launcher script
echo.
echo End user experience:
echo   1. Double-click DeskPulse-Setup.exe
echo   2. Enter Raspberry Pi IP
echo   3. DeskPulse installs and starts automatically
echo   4. Teal icon appears in system tray
echo.
echo To test:
echo   .\dist\DeskPulse-Setup.exe
echo.
pause
