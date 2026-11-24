@echo off
setlocal
cd /d "%~dp0"
title GhostLead Local Workspace
if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
  if errorlevel 1 goto :fail
)
if not exist ".venv\ghostlead-installed" (
  echo Installing GhostLead dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
  echo installed>".venv\ghostlead-installed"
)
echo.
echo GhostLead is starting at http://127.0.0.1:8000
echo Open the address in your browser. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto :fail
exit /b 0
:fail
echo.
echo Startup failed. Check Python installation, internet connection, or port 8000.
pause
exit /b 1
