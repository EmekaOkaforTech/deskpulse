@echo off
REM DeskPulse Windows Installer Builder
REM Creates standalone .exe with PyInstaller

echo ========================================
echo DeskPulse Windows Installer Builder
echo ========================================
echo.

REM Check if running from correct directory
cd /d "%~dp0\.."
if not exist "app\windows_client" (
    echo ERROR: Must run from deskpulse project root!
    echo Current directory: %CD%
    pause
    exit /b 1
)

echo [1/4] Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found, installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo.
echo [2/4] Building DeskPulse.exe with PyInstaller...
pyinstaller build\windows\deskpulse_client.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [3/4] Creating installer package...
if not exist "dist\DeskPulse-Installer" mkdir "dist\DeskPulse-Installer"

REM Copy built executable
xcopy /E /I /Y "dist\DeskPulse" "dist\DeskPulse-Installer\DeskPulse"

REM Copy installer script
copy "build\windows\install.bat" "dist\DeskPulse-Installer\Install.bat"

REM Copy icon
copy "assets\windows\icon_professional.ico" "dist\DeskPulse-Installer\DeskPulse\"

echo.
echo [4/4] Creating README...
(
echo DeskPulse Windows Desktop Client
echo ================================
echo.
echo Installation:
echo 1. Double-click Install.bat
echo 2. Enter your Raspberry Pi IP address
echo 3. Choose auto-start option
echo 4. Done! Look for teal icon in system tray
echo.
echo Requirements:
echo - Raspberry Pi running DeskPulse backend
echo - Windows 10/11
echo - Local network connection to Pi
echo.
echo Support: https://github.com/EmekaOkaforTech/deskpulse
) > "dist\DeskPulse-Installer\README.txt"

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Installer package: dist\DeskPulse-Installer\
echo.
echo To distribute:
echo   1. Zip the DeskPulse-Installer folder
echo   2. Upload to GitHub Releases
echo   3. Users download, extract, run Install.bat
echo.
echo To test locally:
echo   cd dist\DeskPulse-Installer
echo   Install.bat
echo.
pause
