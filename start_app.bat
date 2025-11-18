@echo off
cd /d "%~dp0"
echo ===============================
echo    Starting Flask Application
echo    Teammate Configuration
echo ===============================
set APP_CONFIG=teammate
echo Environment set: APP_CONFIG=teammate
echo Starting Python...
python run.py
pause