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

echo [1/7] Installing dependencies...
pip install -r requirements-windows.txt --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/7] Creating config directory...
mkdir "%APPDATA%\DeskPulse" 2>nul

echo.
echo [3/7] Creating config file...
echo Enter your Raspberry Pi IP address (e.g., 192.168.10.133):
set /p PI_IP=Pi IP:
echo {"backend_url": "http://%PI_IP%:5000"} > "%APPDATA%\DeskPulse\config.json.tmp"
powershell -Command "[System.IO.File]::WriteAllText('%APPDATA%\DeskPulse\config.json', '{\"backend_url\": \"http://%PI_IP%:5000\"}', [System.Text.UTF8Encoding]::new($false))"

echo.
echo [4/7] Temporarily renaming app/__init__.py...
if exist "app\__init__.py" (
    rename "app\__init__.py" "__init__.py.backup"
)

echo.
echo [5/7] Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); if (-not (Test-Path $Desktop)) { New-Item -ItemType Directory -Path $Desktop -Force | Out-Null }; $Shortcut = $WshShell.CreateShortcut(\"$Desktop\DeskPulse.lnk\"); $Shortcut.TargetPath = '%CD%\start_deskpulse.vbs'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = '%CD%\assets\windows\icon_professional.ico'; $Shortcut.Save()"
if errorlevel 1 (
    echo Warning: Desktop shortcut failed, but you can use start_deskpulse.bat
) else (
    echo Desktop shortcut created successfully!
)

echo.
echo [6/7] Do you want to start DeskPulse automatically with Windows?
set /p AUTO_START=Auto-start (y/n):
if /i "%AUTO_START%"=="y" (
    echo Creating startup shortcut...
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Startup = [Environment]::GetFolderPath('Startup'); $Shortcut = $WshShell.CreateShortcut(\"$Startup\DeskPulse.lnk\"); $Shortcut.TargetPath = '%CD%\start_deskpulse.vbs'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = '%CD%\assets\windows\icon_professional.ico'; $Shortcut.Save()"
    echo Startup shortcut created! DeskPulse will start with Windows.
) else (
    echo Skipping auto-start setup.
)

echo.
echo [7/7] Starting DeskPulse now...
start /B "" "%CD%\start_deskpulse.vbs"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Config file: %APPDATA%\DeskPulse\config.json
echo DeskPulse is now running in your system tray!
echo.
echo How to use:
echo   1. Look for the teal icon in your system tray (bottom-right)
echo   2. Right-click the icon for options
echo   3. Double-click desktop shortcut to start manually
echo.
echo To uninstall: Delete shortcuts and remove from Startup folder
echo.
pause
