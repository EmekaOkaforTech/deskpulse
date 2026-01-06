@echo off
REM Complete DeskPulse Uninstaller
REM Removes ALL traces of DeskPulse for clean testing

echo ========================================
echo DeskPulse Complete Uninstaller
echo ========================================
echo.
echo WARNING: This will remove ALL DeskPulse files and settings.
echo This is for clean testing only.
echo.
pause

echo.
echo [1/6] Stopping DeskPulse processes...
taskkill /F /IM pythonw.exe >nul 2>&1
taskkill /F /IM DeskPulse.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Processes stopped.

echo.
echo [2/6] Removing desktop shortcuts...
del "%USERPROFILE%\Desktop\DeskPulse.lnk" >nul 2>&1
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DeskPulse.lnk" >nul 2>&1
echo Shortcuts removed.

echo.
echo [3/6] Removing config files...
rmdir /S /Q "%APPDATA%\DeskPulse" >nul 2>&1
rmdir /S /Q "%LOCALAPPDATA%\DeskPulse" >nul 2>&1
echo Config removed.

echo.
echo [4/6] Removing old source installation...
echo IMPORTANT: This will delete C:\Users\okafor_dev\deskpulse
echo Only continue if you want to remove the source files.
set /p REMOVE_SOURCE=Remove source folder (y/n):
if /i "%REMOVE_SOURCE%"=="y" (
    REM Change to safe directory before deleting
    cd /d %TEMP%
    if exist "C:\Users\okafor_dev\deskpulse" (
        echo Removing deskpulse folder...
        rmdir /S /Q "C:\Users\okafor_dev\deskpulse"
        echo Source folder removed.
    ) else (
        echo Source folder not found.
    )
) else (
    echo Keeping source folder.
)

echo.
echo [5/6] Cleaning Python cache files...
del /S /Q "%TEMP%\*deskpulse*.tmp" >nul 2>&1
echo Cache cleaned.

echo.
echo [6/6] Final cleanup...
REM Remove any stray files
del "%TEMP%\deskpulse_*.log" >nul 2>&1
echo Cleanup complete.

echo.
echo ========================================
echo Uninstall Complete!
echo ========================================
echo.
echo DeskPulse has been completely removed.
echo You can now test the installer as a new user.
echo.
echo To reinstall:
echo   1. Run the new installer (.exe or Install.bat)
echo   2. Enter Pi IP when prompted
echo   3. Enjoy!
echo.
pause
