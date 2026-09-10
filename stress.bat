@echo off
setlocal
cd /d "%~dp0"
echo ========================================================
echo Launching EC2 Incident Stress Generator...
echo ========================================================
if exist "backend\venv\Scripts\python.exe" (
    backend\venv\Scripts\python.exe trigger_stress.py %*
) else (
    python trigger_stress.py %*
)
