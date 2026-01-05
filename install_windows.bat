@echo off
REM DeskPulse Windows Client - Easy Installer
REM Run this from the deskpulse project folder

echo ========================================
echo DeskPulse Windows Client Installer
echo ========================================
echo.

REM Check if running from correct directory
if not exist "app\windows_client" (
    echo ERROR: Must run from deskpulse project root!
    echo Current directory: %CD%
    echo.
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
pip install -r requirements-windows.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/5] Creating config directory...
mkdir "%APPDATA%\DeskPulse" 2>nul

echo.
echo [3/5] Creating config file...
echo Enter your Raspberry Pi IP address (e.g., 192.168.10.133):
set /p PI_IP=Pi IP:
echo {"backend_url": "http://%PI_IP%:5000"} > "%APPDATA%\DeskPulse\config.json.tmp"
powershell -Command "[System.IO.File]::WriteAllText('%APPDATA%\DeskPulse\config.json', '{\"backend_url\": \"http://%PI_IP%:5000\"}', [System.Text.UTF8Encoding]::new($false))"

echo.
echo [4/5] Temporarily renaming app/__init__.py...
if exist "app\__init__.py" (
    rename "app\__init__.py" "__init__.py.backup"
)

echo.
echo [5/5] Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\DeskPulse.lnk'); $Shortcut.TargetPath = 'pythonw.exe'; $Shortcut.Arguments = '-m app.windows_client'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = '%CD%\assets\windows\icon.ico'; $Shortcut.Save()"

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Desktop shortcut created: DeskPulse.lnk
echo Config file: %APPDATA%\DeskPulse\config.json
echo.
echo To start DeskPulse:
echo   - Double-click the desktop shortcut, OR
echo   - Run: start_deskpulse.bat
echo.
pause
