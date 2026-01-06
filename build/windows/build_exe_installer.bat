@echo off
REM DeskPulse Single-File .exe Installer Builder
REM Creates DeskPulse-Setup.exe for end users

echo ========================================
echo DeskPulse .exe Installer Builder
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

echo [1/5] Checking dependencies...
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
echo [2/5] Creating payload.zip...
REM Create temporary directory for payload
if exist "build\windows\payload_temp" rmdir /S /Q "build\windows\payload_temp"
mkdir "build\windows\payload_temp"

REM Copy required files
xcopy /E /I /Y app "build\windows\payload_temp\app"
xcopy /E /I /Y assets "build\windows\payload_temp\assets"
copy /Y requirements-windows.txt "build\windows\payload_temp\"
copy /Y start_deskpulse.bat "build\windows\payload_temp\"
copy /Y start_deskpulse.vbs "build\windows\payload_temp\"

REM Create payload.zip
cd build\windows\payload_temp
powershell -Command "Compress-Archive -Path * -DestinationPath ..\payload.zip -Force"
cd ..\..\..
rmdir /S /Q "build\windows\payload_temp"

if not exist "build\windows\payload.zip" (
    echo ERROR: Failed to create payload.zip
    pause
    exit /b 1
)
echo Payload created: build\windows\payload.zip

echo.
echo [3/5] Building installer with PyInstaller...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "DeskPulse-Setup" ^
    --icon "assets\windows\icon_professional.ico" ^
    --add-data "build\windows\payload.zip;." ^
    --hidden-import "comtypes.client" ^
    --hidden-import "comtypes.gen" ^
    build\windows\installer_wrapper.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo [4/5] Verifying build...
if not exist "dist\DeskPulse-Setup.exe" (
    echo ERROR: DeskPulse-Setup.exe not found
    pause
    exit /b 1
)

echo Build verified: dist\DeskPulse-Setup.exe

echo.
echo [5/5] Cleaning up...
del /Q "build\windows\payload.zip"
echo Temporary files removed

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Installer: dist\DeskPulse-Setup.exe
echo Size:
dir dist\DeskPulse-Setup.exe | find "DeskPulse-Setup.exe"
echo.
echo To distribute:
echo   1. Upload dist\DeskPulse-Setup.exe to GitHub Releases
echo   2. Users download and double-click to install
echo   3. No ZIP extraction, no command prompt needed
echo.
echo To test locally:
echo   .\dist\DeskPulse-Setup.exe
echo.
pause
