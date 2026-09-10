@echo off
setlocal enabledelayedexpansion

echo ==================================================================
echo       EC2 Monitoring and Incident Analysis System                 
echo       (Agentless SSH-Based Remote EC2 Telemetry)
echo ==================================================================
echo.

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"

if not exist "%BACKEND_DIR%\.env" (
    echo [INFO] Copying backend\.env.example to backend\.env
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
)

if not exist "%FRONTEND_DIR%\.env" (
    echo [INFO] Copying frontend\.env.example to frontend\.env
    copy "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul
)

if "%MODE%"=="setup" goto do_setup
if "%MODE%"=="backend" goto do_backend
if "%MODE%"=="frontend" goto do_frontend
if "%MODE%"=="test" goto do_test
if "%MODE%"=="dev" goto do_all
if "%MODE%"=="all" goto do_all

:do_setup
echo [INFO] Running full setup...
cd /d "%BACKEND_DIR%"
if not exist venv ( python -m venv venv )
call .\venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
python -m alembic upgrade head

cd /d "%FRONTEND_DIR%"
if not exist node_modules ( call npm install )
echo [SUCCESS] Setup complete.
goto end

:do_backend
cd /d "%BACKEND_DIR%"
call .\venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
goto end

:do_frontend
cd /d "%FRONTEND_DIR%"
npm run dev
goto end

:do_test
cd /d "%BACKEND_DIR%"
call .\venv\Scripts\activate.bat
pytest app/tests/ -v
goto end

:do_all
echo [INFO] Freeing ports 8000 and 5173 if occupied...
powershell -NoProfile -Command "try { Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction Stop | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } } catch {} exit 0" >nul 2>&1
echo [INFO] Launching FastAPI Backend (with SSH periodic monitoring) and React Frontend...
start "Backend - FastAPI" cmd /k "cd /d %BACKEND_DIR% && .\venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 2 /nobreak >nul
start "Frontend - Vite" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"
echo [SUCCESS] Services launched:
echo   - Backend API & SSH Monitor: http://localhost:8000
echo   - Frontend React Dashboard:  http://localhost:5173
echo   - API Documentation:         http://localhost:8000/docs
goto end

:end
