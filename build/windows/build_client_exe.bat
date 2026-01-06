@echo off
REM Build DeskPulse Windows Client as standalone .exe
REM This creates a single-file executable with all dependencies

echo ========================================
echo DeskPulse Client .exe Builder
echo ========================================
echo.

REM Change to project root
cd /d "%~dp0\..\..

echo [1/3] Checking dependencies...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)
echo PyInstaller: OK

echo.
echo [2/3] Creating clean app/__init__.py for build...
REM Temporarily replace app/__init__.py with stub (no server dependencies)
copy /Y app\__init__.py app\__init__.py.backup
copy /Y build\windows\app_init_stub.py app\__init__.py

echo Building DeskPulse.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "DeskPulse" ^
    --icon "assets\windows\icon_professional.ico" ^
    --add-data "assets\windows\icon_professional.ico;assets\windows" ^
    --hidden-import "engineio.async_drivers.threading" ^
    --hidden-import "PIL._tkinter_finder" ^
    --exclude-module "Flask" ^
    --exclude-module "flask_socketio" ^
    --exclude-module "flask_talisman" ^
    --exclude-module "cv2" ^
    --exclude-module "numpy" ^
    --exclude-module "sqlite3" ^
    --exclude-module "matplotlib" ^
    --exclude-module "tkinter" ^
    app\windows_client\__main__.py

REM Restore original app/__init__.py
copy /Y app\__init__.py.backup app\__init__.py
del app\__init__.py.backup

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Verifying build...
if not exist "dist\DeskPulse.exe" (
    echo ERROR: DeskPulse.exe not found
    pause
    exit /b 1
)

echo Build verified: dist\DeskPulse.exe
dir dist\DeskPulse.exe | find "DeskPulse.exe"

echo.
echo ========================================
echo Client Build Complete!
echo ========================================
echo.
echo Executable: dist\DeskPulse.exe
echo This .exe will be included in the installer payload
echo.
pause
