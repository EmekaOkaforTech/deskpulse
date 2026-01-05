@echo off
REM DeskPulse Windows Client Launcher
REM Runs without console window

cd /d "%~dp0"
start /B pythonw.exe -m app.windows_client
