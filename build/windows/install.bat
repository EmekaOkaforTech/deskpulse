@echo off
REM DeskPulse Windows Client Installer
REM Installs to %LOCALAPPDATA%\DeskPulse

echo ========================================
echo DeskPulse Installation Wizard
echo ========================================
echo.
echo This will install DeskPulse to your computer.
echo.
pause

REM Set installation directory
set INSTALL_DIR=%LOCALAPPDATA%\DeskPulse
set CURRENT_DIR=%~dp0

echo.
echo [1/6] Checking installation directory...
if exist "%INSTALL_DIR%" (
    echo Previous installation found. Updating...
    REM Stop running instance
    taskkill /F /IM DeskPulse.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
) else (
    echo Installing to: %INSTALL_DIR%
)

echo.
echo [2/6] Copying files...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
xcopy /E /I /Y "%CURRENT_DIR%DeskPulse" "%INSTALL_DIR%"
if errorlevel 1 (
    echo ERROR: Failed to copy files
    pause
    exit /b 1
)

echo.
echo [3/6] Setting up configuration...
echo Enter your Raspberry Pi IP address (e.g., 192.168.10.133):
set /p PI_IP=Pi IP:

REM Create config file
powershell -Command "[System.IO.File]::WriteAllText('%LOCALAPPDATA%\DeskPulse\config.json', '{\"backend_url\": \"http://%PI_IP%:5000\"}', [System.Text.UTF8Encoding]::new($false))"
if errorlevel 1 (
    echo ERROR: Failed to create config
    pause
    exit /b 1
)
echo Config saved: %LOCALAPPDATA%\DeskPulse\config.json

echo.
echo [4/6] Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut(\"$Desktop\DeskPulse.lnk\"); $Shortcut.TargetPath = '%INSTALL_DIR%\DeskPulse.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\assets\windows\icon_professional.ico'; $Shortcut.Description = 'DeskPulse - Posture Monitoring'; $Shortcut.Save()"
if errorlevel 1 (
    echo Warning: Desktop shortcut creation failed
) else (
    echo Desktop shortcut created!
)

echo.
echo [5/6] Auto-start with Windows?
set /p AUTO_START=Start DeskPulse when Windows starts (y/n):
if /i "%AUTO_START%"=="y" (
    echo Creating startup shortcut...
    powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Startup = [Environment]::GetFolderPath('Startup'); $Shortcut = $WshShell.CreateShortcut(\"$Startup\DeskPulse.lnk\"); $Shortcut.TargetPath = '%INSTALL_DIR%\DeskPulse.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.IconLocation = '%INSTALL_DIR%\assets\windows\icon_professional.ico'; $Shortcut.Save()"
    echo Auto-start enabled!
) else (
    echo Skipping auto-start.
)

echo.
echo [6/6] Starting DeskPulse...
start "" "%INSTALL_DIR%\DeskPulse.exe"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo DeskPulse is now running in your system tray.
echo Look for the teal icon in the bottom-right corner.
echo.
echo Installed to: %INSTALL_DIR%
echo Config file: %LOCALAPPDATA%\DeskPulse\config.json
echo.
echo To uninstall:
echo   1. Right-click tray icon and select "Exit DeskPulse"
echo   2. Delete folder: %INSTALL_DIR%
echo   3. Delete shortcuts from Desktop and Startup folder
echo.
echo Enjoy better posture!
echo.
pause
