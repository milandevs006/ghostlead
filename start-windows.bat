@echo off
setlocal
cd /d "%~dp0"
title GhostLead Local Workspace - Backend
where python >nul 2>nul
if errorlevel 1 goto :fail
echo Starting GhostLead backend at http://127.0.0.1:8000
echo Start the Next.js frontend separately from the frontend directory.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto :fail
exit /b 0
:fail
echo Startup failed. Check Python, installed requirements, and port 8000.
echo Installation: python -m pip install -r requirements.txt
pause
exit /b 1
