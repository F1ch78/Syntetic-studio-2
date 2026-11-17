@echo off
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3,12)" >nul 2>&1
if errorlevel 1 (
  echo Please install Python 3.12 or newer from python.org, then try again.
  start "" "https://www.python.org/downloads/windows/"
  pause
  exit /b 1
)
echo AI Studio: open http://127.0.0.1:8000 in your browser.
echo Keep this window open. Close it to stop AI Studio.
py -3 server.py
pause
