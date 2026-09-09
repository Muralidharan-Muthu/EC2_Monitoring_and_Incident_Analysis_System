@echo off
setlocal enabledelayedexpansion

echo ==================================================================
echo       EC2 Monitoring and Incident Analysis System                 
echo ==================================================================
echo.

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "AGENT_DIR=%ROOT_DIR%agent"

if not exist "%BACKEND_DIR%\.env" (
    echo [INFO] Copying backend\.env.example to backend\.env
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
)

if not exist "%FRONTEND_DIR%\.env" (
    echo [INFO] Copying frontend\.env.example to frontend\.env
    copy "%FRONTEND_DIR%\.env.example" "%FRONTEND_DIR%\.env" >nul
)

if not exist "%AGENT_DIR%\.env" (
    echo [INFO] Copying agent\.env.example to agent\.env
    copy "%AGENT_DIR%\.env.example" "%AGENT_DIR%\.env" >nul
)

if "%MODE%"=="setup" goto do_setup
if "%MODE%"=="backend" goto do_backend
if "%MODE%"=="frontend" goto do_frontend
if "%MODE%"=="agent" goto do_agent
if "%MODE%"=="dev" goto do_dev
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

cd /d "%AGENT_DIR%"
if not exist venv ( python -m venv venv )
call .\venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
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

:do_agent
cd /d "%AGENT_DIR%"
call .\venv\Scripts\activate.bat
python monitor_agent.py
goto end

:do_dev
echo [INFO] Starting Backend and Frontend in separate windows...
start "Backend - FastAPI" cmd /k "cd /d %BACKEND_DIR% && .\venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
start "Frontend - Vite" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"
echo [SUCCESS] Services launched:
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:5173
goto end

:do_all
echo [INFO] Starting Backend, Frontend, and Agent in separate windows...
start "Backend - FastAPI" cmd /k "cd /d %BACKEND_DIR% && .\venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
start "Frontend - Vite" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"
timeout /t 3 /nobreak >nul
start "Agent - Monitor" cmd /k "cd /d %AGENT_DIR% && .\venv\Scripts\activate.bat && python monitor_agent.py"
echo [SUCCESS] All services launched:
echo   - Backend API:  http://localhost:8000
echo   - Frontend UI:  http://localhost:5173
echo   - Monitoring:   Running in Agent window
goto end

:end
